LAMBDA = lambda: 0


def is_lambda(fun):
    """
    Check whether the given function is a lambda function.

        >>> def not_lambda_fun():
        ...     return None
        ...
        >>> lambda_fun = lambda: None
        ...
        >>> print(
        ...     is_lambda(not_lambda_fun),
        ...     is_lambda(lambda_fun)
        ... )
        ...
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
    return '{}.{}'.format(function.__module__, function.__qualname__)
