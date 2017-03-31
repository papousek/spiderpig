from multiprocessing.pool import ThreadPool
from pytest import raises
from spiderpig.msg import Verbosity
from time import sleep
import spiderpig
import tempfile


def test_configured():
    with spiderpig.spiderpig(a=1, verbosity=Verbosity.INTERNAL):
        assert fun() == (1, 2)
        with spiderpig.configuration(a=2, b=3):
            assert fun() == (2, 3)
        assert fun() == (1, 2)
        assert fun(a=2) == (2, 2)


def test_cached():
    cache_dir = tempfile.mkdtemp()
    with spiderpig.spiderpig(cache_dir, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (1, 2)
        assert spiderpig.execution_context().count_executions(cached_fun) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_b) == 1
    with spiderpig.spiderpig(cache_dir, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (1, 2)
        assert spiderpig.execution_context().count_executions(cached_fun) == 0
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 0
        assert spiderpig.execution_context().count_executions(cached_fun_b) == 0
    with spiderpig.spiderpig(cache_dir, override_cache=True, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun_a() == 1
        assert cached_fun_a() == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 1
    with spiderpig.spiderpig(cache_dir, a=1, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (1, 2)
        assert spiderpig.execution_context().count_executions(cached_fun) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=1) == 0
        assert spiderpig.execution_context().count_executions(cached_fun_b) == 0
    with spiderpig.spiderpig(cache_dir, a=2, verbosity=Verbosity.INTERNAL):
        assert cached_fun() == (2, 2)
        assert spiderpig.execution_context().count_executions(cached_fun) == 1
        assert spiderpig.execution_context().count_executions(cached_fun_a, a=2) == 1


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
    return b


@spiderpig.configured()
def fun(a=None):
    return fun_a(), fun_b()


@spiderpig.cached()
def cached_fun_a(a=None):
    return a


@spiderpig.cached()
def cached_fun_b(b=2):
    return b


@spiderpig.cached()
def cached_fun():
    return cached_fun_a(), cached_fun_b()


class RandomError(Exception):
    pass


@spiderpig.cached()
def errored():
    raise RandomError()


@spiderpig.cached()
def waiting_fun():
    sleep(1)
    return True
