from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

class HealthCheck(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime: Optional[str] = Field(None, description="Service uptime")

