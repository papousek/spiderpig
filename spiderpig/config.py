import argparse


def get_argument_parser():
    p = argparse.ArgumentParser()

    p.add_argument(
        '--cache-dir',
        action='store',
        dest='cache_dir',
        default='cache'
    )
    p.add_argument(
        '--override-cache',
        action='store_true',
        dest='override_cache',
        default=False)
    p.add_argument(
        '--debug',
        action='store_true',
        dest='debug',
        default=False)
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
