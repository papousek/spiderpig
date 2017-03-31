from .execution import Locker, Execution
from .msg import Verbosity
from glob import iglob
import abc
import glob
import math
import os
import pickle
import shutil


class CacheProvider(metaclass=abc.ABCMeta):

    def __init__(self, locker=None, verbosity=Verbosity.INFO, provider=None):
        self._locker = locker if locker else (provider._locker if provider else Locker(verbosity=verbosity))
        self._verbosity = verbosity
        self._provider = provider

    @abc.abstractmethod
    def prepare(self):
        pass

    @abc.abstractmethod
    def get_or_execute(self, execution, already_exclusive=False):
        pass

    @abc.abstractmethod
    def size(self):
        pass

    @abc.abstractmethod
    def is_valid_cache(self, execution):
        pass

    def lock(self, obj=None, already_exclusive=False):
        return EmptyContext() if already_exclusive else self._locker.lock(obj)

    @property
    def verbosity(self):
        return self._verbosity

    @property
    def provider(self):
        return self._provider

    @abc.abstractmethod
    def clear(self):
        pass


class InMemoryCacheProvider(CacheProvider):

    def __init__(self, verbosity=Verbosity.INFO, locker=None, max_entries=1000, provider=None):
        CacheProvider.__init__(self, locker, verbosity, provider)
        self._max_entries = max_entries
        self._cache = {}
        self._cache_priority = {}

    def prepare(self):
        if self._provider is not None:
            return self._provider.prepare()

    def get_or_execute(self, execution, already_exclusive=False):
        with self.lock(execution, already_exclusive):
            if self.is_valid_cache(execution):
                execution_name = execution.name
                result = self._cache[execution_name]
                self._cache_priority[execution_name] = self._cache_priority.get(execution_name, 0) + 1
                return False, result
            if self._provider is None:
                executed = True
                execution_result = execution()
            else:
                executed, execution_result = self._provider.get_or_execute(execution, already_exclusive=True)
            execution_name = execution.name
            if len(self._cache) >= self._max_entries:
                for cache_key, _ in sorted(self._cache_priority.items(), key=lambda x: x[1])[:self._max_entries // 2]:
                    del self._cache[cache_key]
                self._cache_priority = {}
            self._cache[execution_name] = execution_result
            self._cache_priority[execution_name] = self._cache_priority.get(execution_name, 0) + 1
            return executed, execution_result

    def size(self):
        return len(self._cache)

    def is_valid_cache(self, execution):
        return execution.name in self._cache and all([self.is_valid_cache(e) for e in execution.dependencies])

    def to_serializable(self):
        return {
            'max_entries': self._max_entries,
        }

    @staticmethod
    def from_serializable(serializable, verbosity):
        return InMemoryCacheProvider(verbosity, max_entries=serializable['max_entries'])

    def clear(self, recursively=True):
        self._cache = {}
        self._cache_priority = {}
        if recursively and self._provider is not None:
            self._provider.clear()


class StorageCacheProvider(CacheProvider):

    def __init__(self, storage, verbosity=Verbosity.INFO, locker=None, override=False, provider=None):
        CacheProvider.__init__(self, locker, verbosity, provider)
        self._storage = storage
        self._override = override
        self._time = None

    def prepare(self):
        with self.lock():
            self._storage.write_info(init=True)
            self._time = self._storage.read_info_time()
            self._storage.write_info(override_time=self._time)
            for _ in self._storage.read_executions():
                pass
            if self._provider is not None:
                self._provider.prepare()

    def get_or_execute(self, execution, already_exclusive=False):
        with self.lock(execution, already_exclusive):
            if self.is_valid_cache(execution):
                return False, self._storage.read_execution_result(execution)
            if self._provider is None:
                executed = True
                execution()
            else:
                executed, self._provider.get_or_execute(execution, already_exclusive=True)
            self._storage.write_execution_result(execution)
        return executed, self._storage.read_execution_result(execution)

    def size(self):
        with self.lock():
            return sum(1 for _ in self._storage.read_executions())

    def is_valid_cache(self, execution, reread=True):
        if reread:
            execution = self._storage.read_execution(execution)
            if execution is None:
                return False
        execution_time = self._storage.read_execution_time(execution)
        if self._override and execution_time < self._time:
            return False
        return execution_time >= self._get_execution_dependencies_max_time(execution) and all([self.is_valid_cache(d, reread=False) for d in execution.dependencies])

    def clear(self, recursively=True):
        self._storage.clear()
        if recursively and self._provider:
            self._provider.clear(recursively)

    def _get_execution_dependencies_max_time(self, execution):
        times = [self._storage.read_execution_time(d) for d in execution.dependencies]
        times = [(t if t is not None else math.inf) for t in times]
        if len(times) == 0:
            return - math.inf
        return max(times)


class Storage(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def delete_execution_result(self, execution):
        pass

    @abc.abstractmethod
    def write_execution_result(self, execution):
        pass

    @abc.abstractmethod
    def read_execution_result(self, execution):
        pass

    @abc.abstractmethod
    def read_execution_time(self, execution):
        pass

    @abc.abstractmethod
    def read_execution(self, execution):
        pass

    @abc.abstractmethod
    def read_info(self):
        pass

    @abc.abstractmethod
    def read_info_time(self):
        pass

    @abc.abstractmethod
    def write_info(self, **kwargs):
        pass

    @abc.abstractmethod
    def read_executions(self, function=None):
        pass

    @abc.abstractmethod
    def clear(self):
        pass


class FileStorage(Storage):

    def __init__(self, directory, verbosity=Verbosity.INFO):
        self._directory = directory
        self._verbosity = verbosity

    def delete_execution_result(self, execution):
        for filename in [self._get_filename(execution.name, 'execution.info.pickle'), self._get_filename(execution.name, 'execution.pickle')]:
            try:
                os.remove(filename)
            except OSError:
                pass

    def write_execution(self, execution):
        filename = self._get_filename(execution.name, 'execution.info.pickle', prepare=True)
        with open(filename, 'wb') as f:
            pickle.dump(execution.to_serializable(), f)

    def write_execution_ready(self, execution):
        filename = self._get_filename(execution.name, 'execution.ready', prepare=True)
        open(filename, 'a').close()

    def is_execution_ready(self, execution):
        return os.path.exists(self._get_filename(execution.name, 'execution.ready', prepare=False))

    def write_execution_result(self, execution):
        execution_result = execution()
        filename = self._get_filename(execution.name, 'execution.pickle', prepare=True)
        with open(filename, 'wb') as f:
            pickle.dump(execution_result, f)
        self.write_execution(execution)
        self.write_execution_ready(execution)

    def read_execution_result(self, execution):
        if not self.is_execution_ready(execution):
            return None
        filename = self._get_filename(execution.name, 'execution.pickle')
        with open(filename, 'rb') as f:
            return pickle.load(f)

    def read_execution_time(self, execution):
        if not self.is_execution_ready(execution):
            return None
        filename = self._get_filename(execution.name, 'execution.pickle')
        return os.path.getmtime(filename)

    def read_execution(self, execution):
        if not self.is_execution_ready(execution):
            return None
        filename = self._get_filename(execution.name, 'execution.info.pickle')
        with open(filename, 'rb') as f:
            return Execution.from_serializable(pickle.load(f))

    def read_executions(self, function=None):
        if function is None:
            walker = iglob('{}/**/**.execution.info.pickle'.format(self._directory), recursive=True)
        else:
            walker = iglob('{}/{}/*.execution.info.pickle'.format(self._directory, function.name.replace('.', '/')))
        for path in walker:
            with open(path, 'rb') as f:
                yield Execution.from_serializable(pickle.load(f))

    def read_info(self):
        filename = self._get_filename('info', 'pickle')
        if not os.path.exists(filename):
            return {}
        with open(filename, 'rb') as f:
            return pickle.load(f)

    def read_info_time(self):
        filename = self._get_filename('info', 'pickle')
        if not os.path.exists(filename):
            return None
        return os.path.getmtime(filename)

    def write_info(self, **kwargs):
        info = self.read_info()
        for key, value in kwargs.items():
            info[key] = value
        filename = self._get_filename('info', 'pickle', prepare=True)
        with open(filename, 'wb') as f:
            pickle.dump(info, f)

    def clear(self):
        for f in glob.iglob('{}/*'.format(self._directory)):
            try:
                os.remove(f)
            except IsADirectoryError:
                shutil.rmtree(f, ignore_errors=True)

    def _get_filename(self, object_name, extension, prepare=False):
        filename = '{}/{}.{}'.format(self._directory, object_name.replace('.', '/'), extension)
        if prepare:
            directory = os.path.dirname(filename)
            if not os.path.exists(directory):
                os.makedirs(directory)
        return filename


class EmptyContext:

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
