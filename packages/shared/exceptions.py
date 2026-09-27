class CodeAtlasException(Exception):
    """Base domain exception for CodeAtlas."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundException(CodeAtlasException):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(
            message=f"{entity} with id '{entity_id}' not found.",
            code="ENTITY_NOT_FOUND",
            status_code=404,
            details={"entity": entity, "entity_id": entity_id}
        )


class AuthenticationException(CodeAtlasException):
    def __init__(self, message: str = "Invalid authentication credentials."):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=401
        )


class AuthorizationException(CodeAtlasException):
    def __init__(self, message: str = "You do not have permission to access this resource."):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403
        )


class ConflictException(CodeAtlasException):
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details={"field": field} if field else {}
        )


class ValidationException(CodeAtlasException):
    def __init__(self, message: str, errors: list = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"errors": errors or []}
        )
