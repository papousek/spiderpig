from spiderpig.execution import Function
from clint.textui import indent
import spiderpig.msg as msg
import spiderpig


def execute(function_name=None):
    storage = spiderpig.storage()
    function = Function.from_name(function_name) if function_name else None
    msg.print_info('Available cached executions:')
    with indent(4):
        for execution in sorted(storage.read_executions(function), key=lambda e: e.__str__()):
            msg.print_info('{}: {}'.format(execution, execution.name))
