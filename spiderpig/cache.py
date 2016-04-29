from . import msg
from collections import defaultdict
from functools import reduce
from spiderpig.func import function_name
from threading import currentThread, RLock
from time import time
import abc
import hashlib
import importlib
import inspect
import json
import os
import pandas
import pickle
import re


class Function:

    _locks = defaultdict(lambda: RLock())
    _locks_lock = RLock()

    _dependencies = defaultdict(list)
    _dependency_names = defaultdict(set)

    def __init__(self, raw_function):
        self._raw_function = raw_function

    def add_dependency(self, function):
        name = self.name
        with self.lock:
            if function.name not in self._dependency_names[name]:
                self._dependencies[name].append(function)
                self._dependency_names[name].add(function.name)

    @property
    def arguments(self):
        if hasattr(self.raw_function, '__wrapped__'):
            return inspect.getargspec(self.raw_function.__wrapped__).args
        else:
            return inspect.getargspec(self.raw_function).args

    @property
    def dependencies(self):
        with self.lock:
            return list(Function._dependencies[self.name])

    @property
    def dependent_arguments(self):
        return set(self.arguments) | reduce(
            lambda a, b: a | b,
            [d.dependent_arguments for d in self.dependencies],
            set()
        )

    @staticmethod
    def from_name(function_name):
        matched = re.match('(.*)\.(\w+)', function_name)
        module = importlib.import_module(matched.groups()[0])
        return Function(getattr(module, matched.groups()[1]))

    @property
    def lock(self):
        with Function._locks_lock:
            return Function._locks[self.name]

    @property
    def name(self):
        return function_name(self.raw_function)

    @property
    def raw_function(self):
        return self._raw_function

    def __call__(self, **kwargs):
        return self.raw_function(**kwargs)

    def __eq__(self, other):
        if not hasattr(other, 'raw_function'):
            return False
        else:
            return other.raw_function == self.raw_function

    def __str__(self):
        return self.name


class ExecutionContext:

    def __init__(self, cache_provider):
        self._cache_provider = cache_provider
        self._execution_chain = defaultdict(list)
        self._global_kwargs = dict()
        self._kwargs = defaultdict(lambda: defaultdict(dict))
        self._lock = RLock()

    @property
    def cache_provider(self):
        return self._cache_provider

    def add_global_kwargs(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                self._global_kwargs[key] = value

    def execute(self, raw_function, persist, **kwargs):
        function = Function(raw_function)
        cache_kwargs = self._get_kwargs(function, **kwargs)
        cache = self.cache_provider.get(function, persist, dict(self._global_kwargs), **cache_kwargs)
        if cache in self._execution_chain[currentThread()]:
            raise Exception('There is an execution cycle: {}.'.format(
                cache.function.name
            ))
        for execution_segment, _ in self._execution_chain[currentThread()]:
            execution_segment.add_dependency(cache)
            execution_segment.function.add_dependency(cache.function)
        self._execution_chain[currentThread()].append((cache, cache_kwargs))
        result = cache.value
        self._execution_chain[currentThread()].pop()
        return result

    def _get_kwargs(self, function, **cache_kwargs):
        execution_chain = self._execution_chain[currentThread()]
        valid_args = function.arguments
        for execution_segment, segment_kwargs in execution_chain[::-1]:
            for key, value in segment_kwargs.items():
                if key in valid_args and key not in cache_kwargs:
                    cache_kwargs[key] = value
        with self._lock:
            for key, value in self._global_kwargs.items():
                if key in valid_args and key not in cache_kwargs:
                    cache_kwargs[key] = value
        return cache_kwargs


class CacheProvider:

    def __init__(self, storage, debug=False):
        self._storage = storage
        self._memory = {}
        self._memory_lock = RLock()
        self._debug = debug

    def get(self, function, persistent, context_kwargs, **kwargs):
        if not hasattr(self, '_memory'):
            raise Exception('The constructor has not been called properly!')
        with self._memory_lock:
            cache = self.provide(function, persistent, context_kwargs, **kwargs)
            if cache.name in self._memory:
                return self._memory[cache.name]
            self._memory[cache.name] = cache
            return cache

    def provide(self, function, persistent, context_kwargs, **kwargs):
        return Cache(self._storage, function, persistent, context_kwargs, debug=self._debug, **kwargs)

    @property
    def storage(self):
        return self._storage


class Cache:

    _locks = defaultdict(lambda: RLock())
    _locks_lock = RLock()

    def __init__(self, storage, function, persistent, context_kwargs, debug=False, **kwargs):
        self._function = function
        self._kwargs = kwargs
        self._storage = storage
        self._value = None
        self._loaded = False
        self._dependencies = []
        self._debug = debug
        self._persistent = persistent
        self._context_kwargs = context_kwargs

    def add_dependency(self, cache):
        if cache.name not in [c.name for c in self._dependencies]:
            self._dependencies.append(cache)

    @property
    def context_kwargs(self):
        return dict(self._context_kwargs)

    @property
    def dependencies(self):
        return list(self._dependencies)

    @property
    def function(self):
        return self._function

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def lock(self):
        with Cache._locks_lock:
            return Cache._locks[self.name]

    @property
    def name(self):
        context_kwargs = {}
        for arg in self.function.dependent_arguments:
            if arg in self._context_kwargs and arg not in self.kwargs:
                context_kwargs[arg] = self._context_kwargs[arg]
        return hashlib.sha1((
            self.function.name + _serialize(self.kwargs) + _serialize(context_kwargs)
        ).encode()).hexdigest()

    @property
    def persistent(self):
        return self._persistent

    @property
    def value(self):
        if self._loaded:
            return self._value
        else:
            self._value = self._storage.get(self)
        return self._value

    def __call__(self):
        time_before = time()
        result = self.function(**self.kwargs)
        if self.persistent and self._debug:
            msg.info('computing cache {} for function {} with the following parameters took {} seconds:'.format(
                self.name, self.function.name, time() - time_before
            ))
            for key, value in sorted(self.kwargs.items()):
                msg.info('    {}: {}'.format(key, value))
        return result


class CacheStorage(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, cache):
        pass

    @abc.abstractmethod
    def get_cache_info(self, cache):
        pass

    @abc.abstractmethod
    def get_function_dependencies(self, cache):
        pass

    @abc.abstractmethod
    def get_function_info(self, function):
        pass

    @abc.abstractmethod
    def get_info(self):
        pass

    @abc.abstractmethod
    def functions(self):
        pass

    @abc.abstractmethod
    def write_cache_info(self, cache, **kwargs):
        pass

    @abc.abstractmethod
    def write_function_info(self, function, **kwargs):
        pass

    @abc.abstractmethod
    def write_info(self, **kwargs):
        pass


class PickleStorage:

    def __init__(self, directory, override=False, debug=False):
        self._directory = directory
        self._lock = RLock()
        self._override = override
        self._debug = debug

    def caches(self, function):
        self.load_function_dependencies(function)
        function_dir = '{}/{}'.format(self._directory, function.name)
        cache_infos = [f for f in os.listdir(function_dir) if f.endswith('.info.pickle')]
        result = []
        for cache_info_filename in cache_infos:
            cache_info = self._read_file(os.path.join(function_dir, cache_info_filename))
            result.append(Cache(self, function, True, cache_info['context_kwargs'], **cache_info['kwargs']))
        return result

    def get(self, cache):
        self.load_function_dependencies(cache.function)
        with cache.lock:
            if self.is_valid(cache):
                cache_info = self.get_cache_info(cache)
                filename = self.cache_filename(cache)
                self.write_cache_info(cache, hit=cache_info.get('hit', 0) + 1)
                if self._debug:
                    msg.info('reading cache {} with parameters: '.format(filename))
                    for key, value in sorted(cache_info['kwargs'].items()):
                        msg.info('    {}: {}'.format(key, value))
                return self._read_file(filename)
            else:
                return self._write(cache)

    def get_cache_info(self, cache):
        with cache.lock:
            result = self._read_file(self.cache_filename(cache, 'info.pickle'))
            return result if result is not None else {}

    def load_function_dependencies(self, function):
        info = self.get_function_info(function)
        for dep in info.get('dependencies', []):
            dep_function = Function.from_name(dep)
            self.load_function_dependencies(dep_function)
            function.add_dependency(dep_function)

    def get_function_info(self, function):
        with function.lock:
            result = self._read_file(self.function_filename(function))
            return result if result is not None else {}

    def get_info(self):
        with self._lock:
            result = self._read_file(self.filename())
            return result if result is not None else {}

    @property
    def functions(self):
        return [Function.from_name(n) for n in os.listdir(self._directory) if os.path.isdir(os.path.join(self._directory, n))]

    def write_cache_info(self, cache, **kwargs):
        with cache.lock:
            info = self.get_cache_info(cache)
            for key, value in kwargs.items():
                info[key] = value
            self._write_file(self.cache_filename(cache, 'info.pickle'), info)

    def write_function_info(self, function, **kwargs):
        with function.lock:
            info = self.get_function_info(function)
            for key, value in kwargs.items():
                info[key] = value
            self._write_file(self.function_filename(function), info)

    def write_info(self, **kwargs):
        with self._lock:
            info = self.get_info()
            for key, value in kwargs.items():
                info[key] = value
            self._write_file(self.filename(), info)

    def is_valid(self, cache):
        if self._override:
            return False
        if not os.path.exists(self.cache_filename(cache)) and \
                not os.path.exists(self.cache_filename(cache, 'pickle.dataframe')):
            return False

        def _is_valid(info_filename):
            info = self._read_file(info_filename)
            if info is None:
                info = {}
            dependencies = info.get('dependencies', {})
            for dep_file, dep_stamp in dependencies.items():
                dep_info = self._read_file(dep_file)
                if dep_info is None:
                    return False
                if dep_info['stamp'] != dep_stamp:
                    return False
                if not _is_valid(dep_file):
                    return False
            return True

        with self._lock:
            return _is_valid(self.cache_filename(cache, 'info.pickle'))

    def cache_filename(self, cache, extension='pickle'):
        return '{}/{}/{}.{}'.format(
            self._directory,
            cache.function.name,
            cache.name,
            extension
        )

    def function_filename(self, function, extension='pickle'):
        return '{}/{}/info.{}'.format(
            self._directory,
            function.name,
            extension
        )

    def filename(self, extension='pickle'):
        return '{}/storage.{}'.format(
            self._directory,
            extension
        )

    def _read_file(self, filename):
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                return pickle.load(f)
        elif os.path.exists('{}.dataframe'.format(filename)):
            return pandas.read_pickle('{}.dataframe'.format(filename))
        else:
            return None

    def _write(self, cache):
        value = cache()
        if not cache.persistent:
            return value
        with self._lock:
            cache_stamp = self.get_info().get('next_stamp', 0)
            self.write_info(next_stamp=cache_stamp + 1)
        with cache.lock:
            dependencies = {}
            with self._lock:
                for dep_cache in cache.dependencies:
                    dependencies[self.cache_filename(dep_cache, 'info.pickle')] = self.get_cache_info(dep_cache)['stamp']
            self._write_file(self.cache_filename(cache), value)
            self.write_cache_info(
                cache,
                kwargs=cache.kwargs,
                context_kwargs=cache.context_kwargs,
                stamp=cache_stamp,
                dependencies=dependencies,
                function=cache.function.name
            )
        with cache.function.lock:
            dependencies = self.get_function_info(cache.function).get('dependencies', [])
            for dep_fun in cache.function.dependencies:
                dependencies.append(dep_fun.name)
            self.write_function_info(cache.function, dependencies=list(set(dependencies)))
        return value

    def _write_file(self, filename, data):
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        if isinstance(data, pandas.DataFrame):
            data.to_pickle('{}.dataframe'.format(filename))
        else:
            with open(filename, 'wb') as f:
                pickle.dump(data, f)


def _serialize(x):
    try:
        return json.dumps(x, sort_keys=True)
    except TypeError:
        if isinstance(x, dict):
            return json.dumps(sorted([(k, _serialize(v)) for (k, v) in x.items()]), sort_keys=True)
        elif isinstance(x, list):
            return json.dumps([_serialize(v) for v in x])
        else:
            return json.dumps({
                'class': str(x.__class__),
                'data': x.__dict__,
            }, sort_keys=True)
