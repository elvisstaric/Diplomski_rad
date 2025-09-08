from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class PingRequest(BaseModel):
    url: str = Field(..., description="URL to ping")
class TestRequest(BaseModel):
    test_id: str = Field(..., description="Test ID")
    target_url: str = Field(..., description="Target URL")
    dsl_script: str = Field(..., description="DSL script")
    swagger_docs: Optional[str] = Field(None, description="Swagger docs (optional)")
    auth_credentials: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Auth credentials")
    
class TestStatus(BaseModel):
    test_id: str = Field(..., description="Test ID")
    status: str = Field(..., description="Test status")
    progress: float = Field(..., ge=0.0, le=100.0, description="Test progress")
    start_time: datetime = Field(..., description="Test start time")
    end_time: Optional[datetime] = Field(None, description="Test end time")
    test_duration: Optional[int] = Field(None, description="Test duration in seconds")
    results: Dict[str, Any] = Field(default_factory=dict, description="Test results")
    error: Optional[str] = Field(None, description="Test error")

class TestTask(BaseModel):
    test_id: str = Field(..., description="Test ID")
    target_url: str = Field(..., description="Target URL")
    dsl_script: str = Field(..., description="DSL script")
    swagger_docs: Optional[str] = Field(None, description="Swagger docs (optional)")
    auth_credentials: Dict[str, Any] = Field(default_factory=dict, description="Auth credentials")
    created_at: str = Field(..., description="Task creation time")

class TestResult(BaseModel):
    test_id: str = Field(..., description="Test ID")
    worker_id: str = Field(..., description="Worker ID")
    total_requests: int = Field(..., ge=0, description="Total requests")
    successful_requests: int = Field(..., ge=0, description="Successful requests")
    failed_requests: int = Field(..., ge=0, description="Failed requests")
    total_latency: float = Field(..., ge=0.0, description="Total latency")
    max_latency: float = Field(..., ge=0.0, description="Max latency")
    min_latency: float = Field(..., ge=0.0, description="Min latency")
    avg_latency: float = Field(..., ge=0.0, description="Avg latency")
    error_details: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")
    start_time: datetime = Field(..., description="Test start time")
    end_time: datetime = Field(..., description="Test end time")

    @property
    def success_rate(self):
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def failure_rate(self):
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
