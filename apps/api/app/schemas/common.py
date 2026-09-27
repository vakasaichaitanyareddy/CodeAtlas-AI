from typing import Generic, List, Optional, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard unified API response envelope."""
    success: bool = True
    data: T
    message: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated collection response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class ErrorDetail(BaseModel):
    code: str
    message: str
    status: int
    request_id: Optional[str] = None
    details: Optional[dict] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
