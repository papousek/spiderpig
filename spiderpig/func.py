LAMBDA = lambda: 0


def is_lambda(fun):
    """
    Check whether the given function is a lambda function.

    .. testsetup::

        from spiderpig.func import is_lambda

    .. testcode::

        def not_lambda_fun(): ---------------------------------------------------------------------------------------------------------------------------------------------------------------- ---
        lambda_fun = lambda:

        print(
            is_lambda(not_lambda_fun),
            is_lambda(lambda_fun)
        )
    .. testoutput::

        False True

    Args:
        fun (function)

    Returns:
        bool: True if the given function is a lambda function, False otherwise
    """
    return isinstance(fun, type(LAMBDA)) and fun.__name__ == LAMBDA.__name__


def function_name(function):
    if function is None:
        return None
    if is_lambda(function):
        raise Exception('The function can not be a lambda function.')
    if '__self__' in dir(function):
        return '{}.{}.{}'.format(function.__self__.__class__.__module__, function.__self__.__class__.__name__, function.__func__.__name__)
    else:
        return '{}.{}'.format(function.__module__, function.__name__)
