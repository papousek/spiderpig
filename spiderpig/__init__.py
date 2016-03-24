#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argcomplete
from . import commands, config
from . import cache as spcache
from .commands import common
from functools import wraps


_EXECUTION_CONTEXT = None


def init_spiderpig(directory, override_cache=False, debug=False, **global_kwargs):
    global _EXECUTION_CONTEXT
    storage = spcache.PickleStorage(directory, override=override_cache, debug=debug)
    cache_provider = spcache.CacheProvider(storage, debug=debug)
    _EXECUTION_CONTEXT = spcache.ExecutionContext(cache_provider)
    _EXECUTION_CONTEXT.add_global_kwargs(**global_kwargs)


def execution_context():
    global _EXECUTION_CONTEXT
    if _EXECUTION_CONTEXT is None:
        raise Exception('The execution context is not initialized.')
    return _EXECUTION_CONTEXT


class spiderpig:

    def __init__(self, cached=True):
        self._cached = cached

    def __call__(self, func):

        @wraps(func)
        def _wrapper(**kwargs):
            return execution_context().execute(func, self._cached, **kwargs)

        return _wrapper


def run_spiderpig(command_packages, argument_parser=None):
    parser = config.get_argument_parser() if argument_parser is None else argument_parser
    subparsers = parser.add_subparsers()
    for command_package in command_packages:
        commands.register_submodule_commands(subparsers, command_package)
    commands.register_submodule_commands(subparsers, common)
    argcomplete.autocomplete(parser)
    args = vars(parser.parse_args())

    args = config.process_kwargs(args)
    init_spiderpig(args['cache_dir'], **args)

    commands.execute(args)
