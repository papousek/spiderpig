from pytest import raises
from spiderpig.exceptions import ValidationError
from spiderpig.execution import Function, ExecutionContext, Execution
from spiderpig.func import function_name


def test_function():
    fun = Function.from_name('spiderpig.func.function_name')
    assert fun is not None
    assert fun.arguments == ['function']
    assert fun(function_name) == 'spiderpig.func.function_name'
    assert fun(function=Function.from_name) == 'spiderpig.execution.Function.from_name'
    dep_fun = Function.from_name('spiderpig.func.is_lambda')
    fun.add_dependency(dep_fun)
    assert fun.dependencies == [dep_fun]
    assert Function.from_name('spiderpig.func.function_name').dependencies == [dep_fun]
    assert fun == Function.from_name('spiderpig.func.function_name')
    assert fun.dependent_arguments == {'function', 'fun'}
    assert fun.name == 'spiderpig.func.function_name'
    assert fun.raw_function is function_name
    s_fun = Function.from_serializable(fun.to_serializable())
    assert s_fun == fun
    with raises(ImportError):
        Function.from_name('aaa.bbb')


def test_execution():
    reset_calls()
    execution = Execution(fun_a, {}, a=1)
    s_execution = Execution.from_serializable(execution.to_serializable())
    assert s_execution == execution
    assert execution() == 1
    assert get_calls('a') == [{'a': 1}]


def test_execution_context():
    reset_calls()
    context = ExecutionContext()
    context.add_global_kwargs(a=2)
    assert context.execute(fun_a) == 2
    assert get_calls('a') == [{'a': 2}]
    assert context.count_executions(fun_a, a=2) == 1
    assert context.count_executions(fun_a, a=1) == 0
    reset_calls()
    assert context.execute(fun_a, a=3) == 3
    assert get_calls('a') == [{'a': 3}]
    with raises(ValidationError):
        context.execute(fun_a, 1, a=2)


_CALLS = {}


def reset_calls():
    global _CALLS
    _CALLS = {}


def get_calls(name):
    global _CALLS
    return _CALLS.get(name, [])


def fun_a(a):
    global _CALLS
    calls = _CALLS.get('a', [])
    calls.append({'a': a})
    _CALLS['a'] = calls
    return a
