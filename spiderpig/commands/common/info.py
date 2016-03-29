from spiderpig import execution_context
from spiderpig.cache import Function
import spiderpig.msg as msg


def execute(function_name=None):
    storage = execution_context().cache_provider.storage
    if function_name is None:
        msg.info('INFO:')
        for key, value in sorted(storage.get_info().items()):
            msg.info('  {}: {}'.format(key, value))
        msg.info('\nFUNCTIONS:')
        for function in storage.functions:
            msg.info('  {}'.format(function.name))
    else:
        function = Function.from_name(function_name)
        msg.info('INFO for {}'.format(function_name))
        for key, value in sorted(storage.get_function_info(function).items()):
            if isinstance(value, list):
                msg.info('  {}:'.format(key))
                for v in value:
                    msg.info('    {}'.format(v))
            else:
                msg.info('  {}: {}'.format(key, value))
        msg.info('\nCACHES:')
        for cache in storage.caches(function):
            msg.info('  {}'.format(cache.name))
            for key, value in sorted(storage.get_cache_info(cache).items()):
                if isinstance(value, dict):
                    msg.info('    {}:'.format(key))
                    for k, v in value.items():
                        msg.info('      {}: {}'.format(k, v))
                else:
                    msg.info('    {}: {}'.format(key, value))
