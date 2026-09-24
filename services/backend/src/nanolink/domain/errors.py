class NanolinkError(Exception):
    pass


class InvalidLongUrl(NanolinkError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class DuplicateLongUrl(NanolinkError):
    pass


class LinkNotFound(NanolinkError):
    pass


class TaskNotFound(NanolinkError):
    pass


class QuotaExceeded(NanolinkError):
    pass


class NotAuthenticated(NanolinkError):
    pass


class NotAuthorized(NanolinkError):
    pass


class DependencyUnavailable(NanolinkError):
    pass
