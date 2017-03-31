from .exceptions import ValidationError, CyclicExecution
from .func import function_name
from .msg import Verbosity, print_debug
from clint.textui import indent
from collections import defaultdict
from functools import reduce
from glob import iglob
from threading import currentThread
from time import time
import filelock
import hashlib
import importlib
import inspect
import json
import os
import re
import tempfile


class Function:

    _dependencies = defaultdict(list)
    _dependency_names = defaultdict(set)

    def __init__(self, raw_function):
        self._raw_function = raw_function

    def add_dependency(self, function):
        name = self.name
        if function.name != name and function.name not in self._dependency_names[name]:
            self._dependencies[name].append(function)
            self._dependency_names[name].add(function.name)

    @property
    def arguments(self):
        if hasattr(self.raw_function, '__wrapped__'):
            return inspect.getargspec(self.raw_function.__wrapped__).args
        else:
            return inspect.getargspec(self.raw_function).args

    @property
    def defaults(self):
        if hasattr(self.raw_function, '__wrapped__'):
            return inspect.getargspec(self.raw_function.__wrapped__).defaults
        else:
            return inspect.getargspec(self.raw_function).defaults

    @property
    def dependencies(self):
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
    def name(self):
        if not hasattr(self, '_name'):
            self._name = function_name(self.raw_function)
        return self._name

    @property
    def raw_function(self):
        return self._raw_function

    def to_serializable(self):
        name = self.name
        return {
            'function_name': name,
            'dependencies': [fun.to_serializable() for fun in Function._dependencies[name]],
        }

    @staticmethod
    def from_serializable(serializable):
        fun = Function.from_name(serializable['function_name'])
        for dep in serializable['dependencies']:
            fun.add_dependency(Function.from_serializable(dep))
        return fun

    @staticmethod
    def clear_dependencies():
        Function._dependencies = defaultdict(list)
        Function._dependency_names = defaultdict(set)

    def __call__(self, *args, **kwargs):
        return self.raw_function(*args, **kwargs)

    def __eq__(self, other):
        if not hasattr(other, 'raw_function'):
            return False
        else:
            return other.raw_function == self.raw_function

    def __str__(self):
        return self.name


class Execution:

    def __init__(self, function, context_kwargs, verbosity=Verbosity.INFO, **kwargs):
        if isinstance(function, Function):
            self._function = function
        elif isinstance(function, str):
            self._function = Function.from_name(function)
        else:
            self._function = Function(function)
        self._context_kwargs = context_kwargs
        self._kwargs = kwargs
        self._value = None
        self._executed = False
        self._dependencies = []
        self._time = None
        self._verbosity = verbosity

    def add_dependency(self, execution):
        if execution.name not in {e.name for e in self._dependencies}:
            self._dependencies.append(execution)

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
        return dict(self._kwargs)

    @property
    def name(self):
        context_kwargs = {}
        for arg in self.function.dependent_arguments:
            if arg in self._context_kwargs and arg not in self.kwargs:
                context_kwargs[arg] = self._context_kwargs[arg]
        return '{}.{}'.format(self.function.name, hashlib.sha1((
            self.function.name + _serialize(self.kwargs) + _serialize(context_kwargs)
        ).encode()).hexdigest())

    def to_serializable(self):
        return {
            'function': self.function.to_serializable(),
            'context_kwargs': self._context_kwargs,
            'kwargs': self.kwargs,
            'dependencies': [e.to_serializable() for e in self._dependencies],
        }

    @staticmethod
    def from_serializable(serializable, verbosity=Verbosity.INFO):
        execution = Execution(
            function=Function.from_serializable(serializable['function']),
            context_kwargs=serializable['context_kwargs'],
            verbosity=verbosity,
            **serializable['kwargs']
        )
        for d in serializable['dependencies']:
            execution.add_dependency(Execution.from_serializable(d, verbosity=verbosity))
        return execution

    @property
    def time(self):
        return self._time

    def __call__(self):
        if not self._executed:
            time_before = time()
            kwargs = self.kwargs
            if 'verbosity' in self._function.arguments:
                kwargs['verbosity'] = self._verbosity
            self._value = self.function(**kwargs)
            self._time = time() - time_before
            self._executed = True
            if self._verbosity > Verbosity.DEBUG:
                print_debug('execution {0} took {1:.3f} seconds'.format(self.name, self._time))
                with indent(4):
                    for key, val in sorted(self.kwargs.items()):
                        print_debug('{}: {}'.format(key, val))
        return self._value

    def __eq__(self, other):
        return self.function == other.function and self.kwargs == other.kwargs and self.context_kwargs == other.context_kwargs

    def __str__(self):
        if not hasattr(self, '_str'):
            defaults = self.function.defaults
            if not isinstance(defaults, tuple):
                defaults = [defaults]

            kwargs = dict(zip(reversed(self.function.arguments), reversed(defaults)))
            kwargs.update(self.kwargs)
            self._str = '{}({})'.format(
                self.function.name,
                ','.join(
                    '{}={}'.format(key, value.fingerprint() if hasattr(value, 'fingerprint') else value)
                    for key, value in sorted(kwargs.items())
                )
            )
        return self._str


class ExecutionContext:

    def __init__(self, cache_provider=None, verbosity=Verbosity.INFO, locker=None):
        self._cache_provider = cache_provider
        self._execution_chain = defaultdict(list)
        self._global_kwargs = {}
        self._execution_count = defaultdict(lambda: 0)
        self._verbosity = verbosity
        self._locker = locker if locker else (cache_provider._locker if cache_provider else Locker())

    @property
    def global_kwargs(self):
        return dict(self._global_kwargs)

    def add_global_kwargs(self, **kwargs):
        with self._locker.lock():
            for key, value in kwargs.items():
                self._global_kwargs[key] = value

    def execute(self, raw_function, *args, use_cache=True, **kwargs):
        function = Function(raw_function)
        arg_names = function.arguments
        args_kwargs = dict(zip(arg_names, args))
        kwarg_intersection = set(args_kwargs.keys()) & set(kwargs)
        if len(kwarg_intersection) > 0:
            raise ValidationError('Can not pass value for {} as both argument and key-word argument.'.format(kwarg_intersection))
        kwargs.update(args_kwargs)
        exec_kwargs = self._get_kwargs(function, **kwargs)
        execution = Execution(function, dict(self._global_kwargs), verbosity=self.verbosity, **exec_kwargs)
        execution_chain = self._execution_chain[currentThread()]
        if execution in execution_chain:
            raise CyclicExecution('There is an execution cycle: {} -> {}'.format(
                execution.function.name,
                [str(e) for e in execution_chain]
            ))
        for execution_segment in execution_chain:
            execution_segment.add_dependency(execution)
            execution_segment.function.add_dependency(execution.function)
        execution_chain.append(execution)
        try:
            executed, result = (True, execution()) if (self._cache_provider is None or not use_cache) else self._cache_provider.get_or_execute(execution)
            with self._locker.lock(execution):
                self._execution_count[str(execution)] += executed
        finally:
            execution_chain.pop()
        return result

    def _get_kwargs(self, function, **cache_kwargs):
        valid_args = function.arguments
        for execution_segment in self._execution_chain[currentThread()][::-1]:
            for key, value in execution_segment.kwargs.items():
                if key in valid_args and key not in cache_kwargs:
                    cache_kwargs[key] = value
        for key, value in self._global_kwargs.items():
            if key in valid_args and key not in cache_kwargs:
                cache_kwargs[key] = value
        return cache_kwargs

    @property
    def verbosity(self):
        return self._verbosity

    def count_executions(self, function, **kwargs):
        return self._execution_count[str(Execution(function, {}, verbosity=self.verbosity, **kwargs))]


def _serialize(x):
    if hasattr(x, 'fingerprint'):
        return json.dumps([
            '{}.{}'.format(x.__class__.__module__, x.__class__.__name__),
            x.fingerprint()
        ], sort_keys=True)
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


class Locker:

    def __init__(self, directory=None, verbosity=Verbosity.INFO):
        self._directory = tempfile.mkdtemp() if directory is None else directory
        self._verbosity = verbosity
        if not os.path.exists(self._directory):
            os.makedirs(self._directory)

    def clear(self):
        for filename in iglob('{}/*.lock'.format(self._directory)):
            try:
                os.remove(filename)
            except OSError:
                pass

    def lock(self, obj=None):
        name = 'spiderpig.global' if obj is None else obj.name
        return LockWrapper(obj, filelock.FileLock('{}/{}.lock'.format(self._directory, name)), self._verbosity)

    def to_serializable(self):
        return {'directory': self._directory}

    @staticmethod
    def from_serializable(serializable):
        return Locker(serializable['directory'])


class LockWrapper:

    def __init__(self, obj, lock, verbosity):
        self._lock = lock
        self._obj = obj
        self._verbosity = verbosity

    def __enter__(self):
        return self._lock.__class__.__enter__(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._lock.__class__.__exit__(self, exc_type, exc_val, exc_tb)

    def __getattr__(self, attr):
            self._lock.__class__
            orig_attr = self._lock.__getattribute__(attr)
            if self._verbosity < Verbosity.INTERNAL or attr not in ['acquire', 'release']:
                return orig_attr
            current_frame = inspect.currentframe()
            call_frame = inspect.getouterframes(current_frame, 3)
            line = call_frame[3]

            def hooked(*args, **kwargs):
                if attr == 'acquire':
                    print_debug('{}:{} trying to lock {}'.format(line[1], line[2], self._obj))
                result = orig_attr(*args, **kwargs)
                if attr == 'acquire':
                    print_debug('{}:{} locking {}'.format(line[1], line[2], self._obj))
                else:
                    print_debug('{}:{} unlocking {}'.format(line[1], line[2], self._obj))
                return self if result is self._obj else result
            return hooked
