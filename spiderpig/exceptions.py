class SpiderpigError(Exception):
    pass


class ValidationError(SpiderpigError):
    pass


class NotInitialized(SpiderpigError):
    pass


class CyclicExecution(SpiderpigError):
    pass
