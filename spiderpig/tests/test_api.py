from multiprocessing.pool import ThreadPool
from pytest import raises
from spiderpig.msg import Verbosity
from time import sleep
import spiderpig
import tempfile


def test_configured():
    with spiderpig.spiderpig(a=1, verbosity=Verbosity.INTERNAL):
        assert fun() == (1, 3)
        with spiderpig.configuration(a=2, b=3):
            assert fun() == (2, 5)
        assert fun() == (1, 3)
        assert fun(a=2) == (2, 4)


def test_cached():
    cache_dir = tempfile.mkdtemp()
    with spiderpig.spiderpig(cache_dir, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (1, 3, 10)
        assert spiderpig.execution_context().count_executions(cached_fun) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_b) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_c) == 1
    with spiderpig.spiderpig(cache_dir, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (1, 3, 10)
        assert spiderpig.execution_context().count_executions(cached_fun) == 0
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 0
        assert spiderpig.execution_context().count_executions(cached_fun_b) == 0
        assert spiderpig.execution_context().count_executions(cached_fun_c) == 0
    with spiderpig.spiderpig(cache_dir, override_cache=True, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun_a() == 1
        assert cached_fun_a() == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 1
    with spiderpig.spiderpig(cache_dir, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (1, 3, 10)
        assert spiderpig.execution_context().count_executions(cached_fun) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 0
        assert spiderpig.execution_context().count_executions(cached_fun_b) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_c) == 0
    with spiderpig.spiderpig(cache_dir, a=2, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (2, 4, 10)
        assert spiderpig.execution_context().count_executions(cached_fun) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=2) == 1


def test_in_memory_entries():
    cache_dir = tempfile.mkdtemp()
    with spiderpig.spiderpig(cache_dir, max_in_memory_entries=10):
        for i in range(100):
            assert cached_fun_a(a=i) == i
        assert spiderpig.cache_provider().size() <= 10
    with spiderpig.spiderpig(cache_dir, max_in_memory_entries=10):
        for i in range(100):
            assert cached_fun_a(a=i) == i
            assert spiderpig.execution_context().count_executions(cached_fun_a, a=i) == 0
            assert spiderpig.cache_provider().size() <= 10
    cache_dir = tempfile.mkdtemp()
    spiderpig.init(cache_dir, max_in_memory_entries=10)
    for i in range(100):
        assert cached_fun_a(a=i) == i
    assert spiderpig.cache_provider().size() <= 10
    spiderpig.terminate()
    spiderpig.init(cache_dir, max_in_memory_entries=10)
    for i in range(100):
        assert cached_fun_a(a=i) == i
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=i) == 0
        assert spiderpig.cache_provider().size() <= 10


def test_exceptions():
    with spiderpig.spiderpig(verbosity=Verbosity.INTERNAL):
        with raises(RandomError):
            errored()
        with raises(RandomError):
            errored()


def test_concurrency():
    cache_dir = tempfile.mkdtemp()
    pool = ThreadPool(4)
    with spiderpig.spiderpig(cache_dir, verbosity=Verbosity.INTERNAL):
        assert pool.map(waiting_fun, [None] * 4) == [True] * 4
        assert spiderpig.execution_context().count_executions(waiting_fun) == 1


@spiderpig.configured()
def fun_a(a=None):
    return a


@spiderpig.configured()
def fun_b(b=2):
    return b + fun_a()


@spiderpig.configured()
def fun(a=None):
    return fun_a(), fun_b()


@spiderpig.cached()
def cached_fun_a(a=None):
    return a


@spiderpig.cached()
def cached_fun_b(b=2):
    return b + cached_fun_a()


@spiderpig.cached()
def cached_fun_c(c=10):
    return c


@spiderpig.cached()
def cached_fun():
    return cached_fun_a(), cached_fun_b(), cached_fun_c()


class RandomError(Exception):
    pass


@spiderpig.cached()
def errored():
    raise RandomError()


@spiderpig.cached()
def waiting_fun():
    sleep(1)
    return True
