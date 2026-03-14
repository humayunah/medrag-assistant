class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        detail: str = "An internal error occurred",
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource", detail: str | None = None):
        super().__init__(
            status_code=404,
            error_code="NOT_FOUND",
            detail=detail or f"{resource} not found",
        )


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            error_code="FORBIDDEN",
            detail=detail,
        )


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=401,
            error_code="UNAUTHORIZED",
            detail=detail,
        )


class ConflictError(AppException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=409,
            error_code="CONFLICT",
            detail=detail,
        )


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=422,
            error_code="VALIDATION_ERROR",
            detail=detail,
        )


class RateLimitError(AppException):
    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            detail=detail,
        )


class ServiceUnavailableError(AppException):
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            detail=detail,
        )
