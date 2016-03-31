import inspect
import pkgutil
from spiderpig import msg


def register_submodule_command(subparsers, submodule, namespace=None):
    if 'command_name' in dir(submodule):
        command_name = submodule.command_name()
    else:
        command_name = submodule.__name__.split('.')[-1].replace('_', '-')
    command_name = command_name if namespace is None else '{}-{}'.format(namespace, command_name)
    subparser = subparsers.add_parser(command_name, help=submodule.__doc__)
    if 'init_parser' in dir(submodule):
        submodule.init_parser(subparser)
    else:
        args, varargs, keywords, defaults = inspect.getargspec(submodule.execute)

        def transform(x):
            return [] if x is None else x
        kwargs = dict(zip(args[-len(transform(defaults)):], transform(defaults)))
        for argname, default in kwargs.items():
            subparser.add_argument('--{}'.format(argname), action='store', default=default, required=False, help='default: {}'.format(default))
        for argname in args:
            if argname not in kwargs:
                subparser.add_argument('--{}'.format(argname), action='store', required=True)
    subparser.set_defaults(func=submodule.execute)


def register_submodule_commands(subparsers, package, namespace=None):
    prefix = package.__name__ + "."
    for importer, module_name, ispkg in pkgutil.iter_modules(package.__path__, prefix):
        if not ispkg:
            submodule = importer.find_module(module_name).load_module(module_name)
            if not is_submodule_command(submodule):
                continue
            register_submodule_command(subparsers, submodule, namespace=namespace)


def is_submodule_command(submodule):
    return hasattr(submodule, 'execute')


def execute(args):
    if 'func' not in args:
        msg.error('You have to choose subcommand!')
        return
    func = args['func']
    allowed_args = inspect.getargspec(func).args
    func_args = {key: value for (key, value) in args.items() if key in allowed_args}
    func(**func_args)
