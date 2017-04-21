from .exceptions import ValidationError
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


class Configuration:

    def __init__(self, configuration=None, **kwargs):
        self._kwargs = process_kwargs(kwargs)
        self._configuration = configuration

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise ValidationError('The key argument has to be a string.')
        if key in self._kwargs:
            return self._kwargs[key]
        if self._configuration is not None and key in self._configuration:
            return self._configuration[key]
        raise KeyError(key)

    def __contains__(self, key):
        return key in self._kwargs or (self._configuration is not None and key in self._configuration)

    def to_serializable(self):
        result = {
            'kwargs': dict(self._kwargs),
        }
        if self._configuration is not None:
            result['configuration'] = self._configuration.to_serializable()
        return result

    @staticmethod
    def from_serializable(serializable):
        configuration = None if 'configuration' not in serializable else Configuration.from_serializable(serializable['configuration'])
        return Configuration(configuration, **serializable['kwargs'])

    def __str__(self):
        return str(self._kwargs)
