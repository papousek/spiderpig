from .msg import Verbosity
import argparse


def get_argument_parser():
    p = argparse.ArgumentParser()

    p.add_argument(
        '--spiderpig-dir',
        action='store',
        dest='spiderpig_dir',
        default='.spiderpig'
    )
    p.add_argument(
        '--override-cache',
        action='store_true',
        dest='override_cache',
        default=False)
    p.add_argument(
        '--verbosity',
        action='store',
        dest='verbosity',
        type=int,
        default=Verbosity.INFO,
        choices=[Verbosity.INFO, Verbosity.DEBUG, Verbosity.VERBOSE, Verbosity.INTERNAL])
    p.add_argument(
        '--max-in-memory-entries',
        action='store',
        dest='max_in_memory_entries',
        default=1000
    )
    return p


def process_kwargs(parsed_kwargs):
    return {key: _convert_kwarg_value(val) for (key, val) in parsed_kwargs.items()}


def _convert_kwarg_value(val):
    if not isinstance(val, str):
        return val
    if val == 'False':
        return False
    elif val == 'True':
        return True
    else:
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            return val
    return val
