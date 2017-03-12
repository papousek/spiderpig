from spiderpig.cache import InMemoryCacheProvider, FileStorage, StorageCacheProvider
from spiderpig.execution import ExecutionContext, Locker
from spiderpig.msg import Verbosity
from spiderpig.tests.test_execution import reset_calls, get_calls, fun_a
import tempfile


def test_in_memory_cache():
    reset_calls()
    provider = InMemoryCacheProvider(max_entries=10)
    context = ExecutionContext(cache_provider=provider)
    for i in range(2):
        for _ in range(2):
            assert context.execute(fun_a, i) == i
    assert get_calls('a') == [{'a': i} for i in range(2)]
    assert provider.size() == 2
    provider.clear()
    for i in range(2):
        for _ in range(2):
            assert context.execute(fun_a, i) == i
    assert get_calls('a') == [{'a': i} for _ in range(2) for i in range(2)]
    provider.clear()
    for i in range(20):
        assert context.execute(fun_a, i) == i
        assert provider.size() <= 10


def test_storage_cache():
    reset_calls()
    storage = FileStorage(tempfile.mkdtemp())
    provider = StorageCacheProvider(storage=storage, locker=Locker(verbosity=Verbosity.INTERNAL))
    context = ExecutionContext(cache_provider=provider)
    for i in range(2):
        for _ in range(2):
            assert context.execute(fun_a, i) == i
    assert get_calls('a') == [{'a': i} for i in range(2)]
    assert provider.size() == 2
    provider.clear()
    for i in range(2):
        for _ in range(2):
            assert context.execute(fun_a, i) == i
    assert get_calls('a') == [{'a': i} for _ in range(2) for i in range(2)]


def test_storage_integration():
    reset_calls()
    storage = FileStorage(tempfile.mkdtemp())
    storage_provider = StorageCacheProvider(storage=storage, locker=Locker(verbosity=Verbosity.INTERNAL))
    in_memory_provider = InMemoryCacheProvider(provider=storage_provider)
    context = ExecutionContext(cache_provider=in_memory_provider)
    for i in range(2):
        for _ in range(2):
            assert context.execute(fun_a, i) == i
    assert get_calls('a') == [{'a': i} for i in range(2)]
    assert storage_provider.size() == 2
    assert in_memory_provider.size() == 2
    in_memory_provider.clear(recursively=False)
    assert storage_provider.size() == 2
    for i in range(2):
        for _ in range(2):
            assert context.execute(fun_a, i) == i
    assert get_calls('a') == [{'a': i} for i in range(2)]
    assert storage_provider.size() == 2
    assert in_memory_provider.size() == 2
    storage_provider.clear()
    for i in range(2):
        for _ in range(2):
            assert context.execute(fun_a, i) == i
    assert get_calls('a') == [{'a': i} for i in range(2)]


def test_storage_with_recursion():
    reset_calls()
    storage = FileStorage(tempfile.mkdtemp())
    storage_provider = StorageCacheProvider(storage=storage, locker=Locker(verbosity=Verbosity.INTERNAL))
    in_memory_provider = InMemoryCacheProvider(provider=storage_provider)
    context = ExecutionContext(cache_provider=in_memory_provider)
    assert context.execute(factorial, 6) == 720


def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
