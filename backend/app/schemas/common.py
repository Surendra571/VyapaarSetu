from typing import Generic, List, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination envelope."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class StandardMessageResponse(BaseModel):
    """Standard success message response."""
    status: str = "success"
    message: str

