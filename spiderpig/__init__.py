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
        def _wrapper(*args, **kwargs):
            def_args = spcache.Function(func).arguments
            for k, v in zip(def_args, args):
                kwargs[k] = v
            return execution_context().execute(func, self._cached, **kwargs)

        return _wrapper


def run_spiderpig(command_packages=None, namespaced_command_packages=None, argument_parser=None, setup_functions=None):
    if command_packages is None:
        command_packages = []
    if namespaced_command_packages is None:
        namespaced_command_packages = {}
    if setup_functions is None:
        setup_functions = []
    parser = config.get_argument_parser() if argument_parser is None else argument_parser
    subparsers = parser.add_subparsers()
    for command_package in command_packages:
        commands.register_submodule_commands(subparsers, command_package)
    for command_namespace, command_package in namespaced_command_packages.items():
        commands.register_submodule_commands(subparsers, command_package, namespace=command_namespace)
    commands.register_submodule_commands(subparsers, common, namespace='spiderpig')
    argcomplete.autocomplete(parser)
    args = vars(parser.parse_args())

    args = config.process_kwargs(args)
    init_spiderpig(args['cache_dir'], **{k: v for (k, v) in args.items() if k != 'func'})

    for setup_fun in setup_functions:
        execution_context().execute(setup_fun, False)
    commands.execute(args)
