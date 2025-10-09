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
    auth_type: Optional[str] = Field("none", description="Auth type: none, basic, bearer, session")
    
class TestStatus(BaseModel):
    test_id: str = Field(..., description="Test ID")
    status: str = Field(..., description="Test status")
    progress: float = Field(..., ge=0.0, le=100.0, description="Test progress")
    start_time: datetime = Field(..., description="Test start time")
    end_time: Optional[datetime] = Field(None, description="Test end time")
    test_duration: Optional[int] = Field(None, description="Test duration in seconds")
    results: Dict[str, Any] = Field(default_factory=dict, description="Test results")
    error: Optional[str] = Field(None, description="Test error")
    target_url: Optional[str] = Field(None, description="Target URL")
    dsl_script: Optional[str] = Field(None, description="DSL script")
    auth_credentials: Dict[str, Any] = Field(default_factory=dict, description="Auth credentials")

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

class DetailedTestAnalysis(BaseModel):
    test_id: str = Field(..., description="Test ID")
    test_summary: Dict[str, Any] = Field(..., description="Basic test statistics")
    endpoint_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Statistics per endpoint")
    error_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="Error pattern analysis")
    time_series_data: Dict[str, List[float]] = Field(default_factory=dict, description="Time series data")
    performance_insights: List[str] = Field(default_factory=list, description="Performance insights")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")

class TestReport(BaseModel):
    test_id: str = Field(..., description="Test ID")
    report_content: str = Field(..., description="Generated report content")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation time")
    analysis_data: DetailedTestAnalysis = Field(..., description="Underlying analysis data")

class CausalExperimentRequest(BaseModel):
    baseline_dsl: str = Field(..., description="Baseline DSL script")
    experiment_description: str = Field(..., description="Description of what to test")
    number_of_tests: int = Field(..., ge=2, le=10, description="Number of test variations to generate")
    target_url: str = Field(..., description="Target URL for testing")
    auth_credentials: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Auth credentials")
    generated_variations: Optional[List[Dict[str, Any]]] = Field(None, description="Pre-generated DSL variations")

class CausalExperimentResult(BaseModel):
    experiment_id: str = Field(..., description="Experiment ID")
    baseline_dsl: str = Field(..., description="Original baseline DSL")
    generated_variations: List[Dict[str, Any]] = Field(..., description="Generated DSL variations")
    test_results: List[Dict[str, Any]] = Field(..., description="Results from all tests")
    causal_analysis: str = Field(..., description="Causal inference analysis report")
    causal_results: Dict[str, Any] = Field(default_factory=dict, description="Raw DoWhy causal analysis results")
    dataframe_info: Dict[str, Any] = Field(default_factory=dict, description="DataFrame information")
    generated_at: datetime = Field(default_factory=datetime.now, description="Experiment completion time")

class GenerateDSLRequest(BaseModel):
    description: str = Field(..., description="Natural language description of the user journey")
    target_domain: Optional[str] = Field(None, description="Target domain (e.g., ecommerce, banking)")
    swagger_docs: Optional[str] = Field(None, description="Swagger docs (optional)")
    api_endpoints: Optional[List[str]] = Field(None, description="API endpoints (optional)")
    user_model: Optional[str] = Field("closed", description="User model type (closed or open)")
    arrival_rate: Optional[float] = Field(None, description="Arrival rate for open model (users per second)")
    session_duration: Optional[float] = Field(None, description="Session duration for open model (seconds)")
    auto_run: Optional[bool] = Field(False, description="Automatically run test after generating DSL")
    target_url: Optional[str] = Field(None, description="Target URL for auto-run test")

class OptimizeDSLRequest(BaseModel):
    dsl_script: str = Field(..., description="Existing DSL script to optimize")
    optimization_goal: str = Field(default="improve performance", description="Goal for optimization")

class DSLResponse(BaseModel):
    dsl_script: str = Field(..., description="Generated or optimized DSL script")
    status: str = Field(..., description="Status of the operation")
    model_used: Optional[str] = Field(None, description="LLM model used")
    explanation: Optional[str] = Field(None, description="Explanation of changes (for optimization)")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    test_id: Optional[str] = Field(None, description="Test ID if auto-run was enabled")
    message: Optional[str] = Field(None, description="Additional message about the operation")
