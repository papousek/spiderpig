from clint.textui import colored, puts


class Verbosity:
    INFO = 0
    DEBUG = 1
    VERBOSE = 2
    INTERNAL = 3


def print_debug(msg):
    puts(colored.yellow(str(msg)))


def print_info(msg):
    puts(colored.blue(str(msg)))


def print_success(msg):
    puts(colored.green(str(msg)))


def print_error(msg):
    puts(colored.red(str(msg)))
