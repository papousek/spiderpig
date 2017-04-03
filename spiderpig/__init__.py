from . import cache
from . import commands, config
from . import execution
from .exceptions import ValidationError, NotInitialized
from .msg import Verbosity
from contextlib import ContextDecorator
from functools import wraps
import argcomplete
import json
import tempfile
import yaml


__VERSION__ = '2.0.0'


_EXECUTION_CONTEXT = None
_CACHE_PROVIDER = None
_STORAGE = None


class spiderpig(ContextDecorator):

    """
    Decorator/context initializing spiderpig.

    Examples
    --------

        >>> @configured()
        ... def fun_a(a=None):
        ...    print('A:', a)
        ...
        >>> @configured()
        ... def fun_b(a=None, b=None):
        ...    fun_a()
        ...    print('B:', b)
        ...
        >>> cache_dir = tempfile.mkdtemp()
        >>> with spiderpig(cache_dir, a=1, b=2):
        ...    fun_b()
        ...    fun_b(a=10, b=20)
        ...
        A: 1
        B: 2
        A: 10
        B: 20

    See also
    --------
    init
    """

    def __init__(self, directory=None, override_cache=False, verbosity=Verbosity.INFO, max_in_memory_entries=1000, config_file=None, **global_kwargs):
        """
        Initialize spiderpig for using it out of command-line tool.

        Parameters
        ----------
        directory: str
            path to a directory used for spiderpig auxiliary files and cache
        override_cache: bool, default False
            True if you want to recompute all spiderpig functions
            regardless of whether there is valid cache available, otherwise False
        verbosity: int, default 0
            increase verbosity level
        max_in_memory_entries: int, default 1000
            maximal number of entries in in-memory cache
        config_file: str
            path to the YAML/JSON file containing key-word parameters to
            override the global configuration
        global_kwargs: dict
            key-word arguments passed to spiderpig functions
        """
        self._directory = directory
        self._override_cache = override_cache
        self._verbosity = verbosity
        self._max_in_memory_entries = max_in_memory_entries
        self._global_kwargs = global_kwargs
        self._config_file = config_file

    def __enter__(self):
        init(self._directory, self._override_cache, self._verbosity, self._max_in_memory_entries, self._config_file, **self._global_kwargs)

    def __exit__(self, *exc):
        terminate()


def init(directory=None, override_cache=False, verbosity=Verbosity.INFO, max_in_memory_entries=1000, config_file=None, **global_kwargs):
    """
    Initialize spiderpig for using it out of command-line tool.

    Parameters
    ----------
    directory: str
        path to a directory used for spiderpig auxiliary files and cache
    override_cache: bool, default False
        True if you want to recompute all spiderpig functions
        regardless of whether there is valid cache available, otherwise False
    verbosity: int, default 0
        increase verbosity level
    max_in_memory_entries: int, default 1000
        maximal number of entries in in-memory cache
    config_file: str
        path to the YAML/JSON file containing key-word parameters to
        override the global configuration
    global_kwargs: dict
        key-word arguments passed to spiderpig functions

    Examples
    --------

        >>> @configured()
        ... def fun_a(a=None):
        ...    print('A:', a)
        ...
        >>> @configured()
        ... def fun_b(a=None, b=None):
        ...    fun_a()
        ...    print('B:', b)
        ...
        >>> cache_dir = tempfile.mkdtemp()
        >>> init(cache_dir, a=1, b=2)
        >>> fun_b()
        A: 1
        B: 2
        >>> fun_b(a=10, b=20)
        A: 10
        B: 20
    """
    global _EXECUTION_CONTEXT
    global _CACHE_PROVIDER
    global _STORAGE
    if config_file is not None:
        with open(config_file, 'r') as f:
            from_config_file = json.load(f.read()) if config_file.endswith('.json') else yaml.load(f.read())
            for key, value in from_config_file.items():
                if hasattr(value, '__len__') and not isinstance(value, str):
                    raise ValidationError('Config "{} ({})" is not scalar.'.format(key, value))
            from_config_file.update(global_kwargs)
            global_kwargs= from_config_file
    if directory is None:
        _CACHE_PROVIDER = cache.InMemoryCacheProvider(max_entries=max_in_memory_entries)
    else:
        _STORAGE = cache.FileStorage(directory if directory else tempfile.mkdtemp())
        _CACHE_PROVIDER = cache.InMemoryCacheProvider(
            provider=cache.StorageCacheProvider(
                storage=_STORAGE, verbosity=verbosity, override=override_cache
            ),
            max_entries=max_in_memory_entries
        )
    _CACHE_PROVIDER.prepare()
    _EXECUTION_CONTEXT = execution.ExecutionContext(
        cache_provider=_CACHE_PROVIDER,
        verbosity=verbosity
    )
    _EXECUTION_CONTEXT.add_global_kwargs(**global_kwargs)


def terminate():
    """
    Terminates spiderpig and clears execution contexts and other auxiliary
    services.
    """
    global _EXECUTION_CONTEXT
    global _CACHE_PROVIDER
    global _STORAGE

    _EXECUTION_CONTEXT = None
    _CACHE_PROVIDER = None
    _STORAGE
    execution.Function.clear_dependencies()


class configuration:

    """
    Context overriding global configuration (key-word arguments) passed to all
    spiderpig functions. The configuration can be given directly as key-word
    arguments or loaded from configuration YAML/JSON file.

    Examples
    --------

        >>> @configured()
        ... def fun(a=None):
        ...     print('A:', a)
        ...
        >>> cache_dir = tempfile.mkdtemp()
        >>> with spiderpig(cache_dir, a=1):
        ...     fun()
        ...     with configuration(a=2):
        ...         fun()
        ...     fun()
        ...
        A: 1
        A: 2
        A: 1
    """

    def __init__(self, config_file=None, **config):
        """
        Override current global configuration.

        Parameters
        ----------
        config_file: str
            path to the YAML/JSON file containing key-word parameters to override
        config: dict
            key-word parameters to override
        """
        self._config = config
        if config_file is not None:
            with open(config_file, 'r') as f:
                from_config_file = json.load(f.read()) if config_file.endswith('.json') else yaml.load(f.read())
                for key, value in from_config_file.items():
                    if hasattr(value, '__len__') and not isinstance(value, str):
                        raise ValidationError('Config "{} ({})" is not scalar.'.format(key, value))
                from_config_file.update(self._config)
                self._config = from_config_file

    def __enter__(self):
        if len(self._config) == 0:
            return
        self._current_exec_context = execution_context()
        global _EXECUTION_CONTEXT
        _EXECUTION_CONTEXT = execution.ExecutionContext(
            cache_provider=_CACHE_PROVIDER,
            verbosity=self._current_exec_context.verbosity
        )
        _EXECUTION_CONTEXT.add_global_kwargs(**self._current_exec_context.global_kwargs)
        _EXECUTION_CONTEXT.add_global_kwargs(**self._config)
        return self

    def __exit__(self, *exc):
        if len(self._config) == 0:
            return
        global _EXECUTION_CONTEXT
        _EXECUTION_CONTEXT = self._current_exec_context


def storage():
    """
    Retrieve the current storage used by spiderpig to persist cache. If
    spiderpig is initialized without directory, there is no storage and this
    function returns None.

    Returns
    -------
    storage currently used by spiderpig to persist cache
    """
    global _STORAGE
    if _STORAGE is None:
        raise NotInitialized('The storage is not initialized.')
    return _STORAGE


def cache_provider():
    """
    Retrieve the current cache provider.
    """
    global _CACHE_PROVIDER
    if _CACHE_PROVIDER is None:
        raise NotInitialized('The cache provider is not initialized.')
    return _CACHE_PROVIDER


def execution_context():
    """
    Retrieve the current execution context.
    """
    global _EXECUTION_CONTEXT
    if _EXECUTION_CONTEXT is None:
        raise NotInitialized('The execution context is not initialized.')
    return _EXECUTION_CONTEXT


class configured:

    """
    Decorator used to annotate spiderpig functions. Parameters for these
    functions are injected from the global configuration.

    See also
    --------
    spiderpig
    init
    cached
    """

    def __init__(self, cached=False, **config):
        """
        Create a decorator instance.

        Parameters
        ----------
        cached: bool, default False
            turn on caching
        config: dict
            key-word parameters to override the global configuration
        """
        self._cached = cached
        self._config = config

    def __call__(self, func):

        @wraps(func)
        def _wrapper(*args, **kwargs):
            def_args = execution.Function(func).arguments
            kwargs.update(dict(zip(def_args, args)))
            with configuration(**self._config):
                return execution_context().execute(func, use_cache=self._cached, **kwargs)

        return _wrapper


class cached(configured):

    """
    Decorator used to annotate cached spiderpig functions. Parameters for these
    functions are injected from the global configuration. Executions are cached
    based on the values of parameters of the given function and its
    dependencies.

    Examples
    --------

        >>> @cached()
        ... def fun(a=None):
        ...     print('executed')
        ...     return a
        ...
        >>> cache_dir = tempfile.mkdtemp()
        >>> with spiderpig(cache_dir, a=1):
        ...     print(fun())
        ...     print(fun())
        ...     print(fun(2))
        ...
        executed
        1
        1
        executed
        2

    See also
    --------
    spiderpig
    init
    configured
    """

    def __init__(self, **config):
        """
        Create a decorator instance.

        Parameters
        ----------
        cached: bool, default False
            turn on caching
        config: dict
            key-word parameters to override the global configuration
        """
        super().__init__(cached=True, **config)


def run_cli(command_packages=None, namespaced_command_packages=None, argument_parser=None, setup_functions=None):
    """
    Run spiderpig command-line application.

    Args:
        command_packages: list of packages containing modules representing
            command-line commands
        namespaced_command_packages: dictionary with packages containing
            modules representing command-line commands; keys are used as
            prefixes for the commands
        argument_parser: custom argument parser (argparse.ArgumentParser instance)
        setup_functions: functions invoked before the main command is executed
    """
    import spiderpig.commands.common as spcommon
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
    commands.register_submodule_commands(subparsers, spcommon, namespace='spiderpig')
    argcomplete.autocomplete(parser)
    args = vars(parser.parse_args())

    args = config.process_kwargs(args)
    with spiderpig(args['spiderpig_dir'], **{k: v for (k, v) in args.items() if k != 'func'}):
        for setup_fun in setup_functions:
            execution_context().execute(setup_fun, False)
        commands.execute(args)
