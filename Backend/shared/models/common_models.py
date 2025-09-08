from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

class BaseResponse(BaseModel):
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    data: Optional[Any] = Field(None, description="Response data")

class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Operation success status (always false)")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    details: Optional[Any] = Field(None, description="Additional error details")

class HealthCheck(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime: Optional[str] = Field(None, description="Service uptime")

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")
    total: Optional[int] = Field(None, description="Total items")

class PaginatedResponse(BaseModel):
    items: list = Field(..., description="List items")
    pagination: PaginationParams = Field(..., description="Pagination information")
    total_pages: int = Field(..., description="Total pages")

