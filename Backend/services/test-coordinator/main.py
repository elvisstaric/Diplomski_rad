from fastapi import FastAPI, HTTPException, Body
from typing import List, Dict, Any
import asyncio
import aio_pika
import json
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
import aiohttp
import time
import sys
import os
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_new_dir = os.path.join(current_dir, '..', '..')
sys.path.insert(0, backend_new_dir)


from shared.models import PingRequest, TestRequest, TestStatus, GenerateDSLRequest, OptimizeDSLRequest, DSLResponse, DetailedTestAnalysis, TestReport, CausalExperimentRequest, CausalExperimentResult
from shared.DSL.main import parse_dsl
from shared.analytics.test_analytics import TestAnalytics
from shared.analytics.causal_analysis import causal_analysis_engine
from modules.utils import ping_backend, calculate_test_progress, format_test_results
from modules.llm_service import llm_service

rabbitmq_connection = None
test_queue = None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rabbitmq_connection, test_queue
    try:
        rabbitmq_connection = await aio_pika.connect_robust(
            "amqp://guest:guest@localhost/"
        )
        channel = await rabbitmq_connection.channel()
        test_queue = await channel.declare_queue("test_tasks", durable=True)
        print("Connected to RabbitMQ")
        asyncio.create_task(check_timeout())
    except Exception as e:
        print(f"RabbitMQ connection error: {e}")
    
    yield
    
    if rabbitmq_connection:
        await rabbitmq_connection.close()

async def check_timeout():
    while True:
        await check_test_timeouts()
        await asyncio.sleep(30)

app = FastAPI(title="Test Coordinator", version="1.0.0", lifespan=lifespan)

active_tests: Dict[str, TestStatus] = {}
completed_tests: Dict[str, TestStatus] = {}
failed_tests: Dict[str, TestStatus] = {}
test_results: Dict[str, Dict[str, Any]] = {}
test_reports: Dict[str, TestReport] = {}

causal_experiments: Dict[str, CausalExperimentResult] = {}

analytics_engine = TestAnalytics()

async def check_test_timeouts():
    current_time = datetime.now()
    for test_id, test_status in list(active_tests.items()):
        if test_status.start_time and test_status.test_duration:
            elapsed = (current_time - test_status.start_time).total_seconds()
            
            test_status.progress = calculate_test_progress(test_status)
            
            timeout_buffer = 600
            timeout_threshold = test_status.test_duration + timeout_buffer
            
            if elapsed > timeout_threshold:
                test_status.status = "failed"
                test_status.end_time = current_time
                test_status.error = f"Test timeout (exceeded {timeout_threshold}s)"
                test_status.progress = 100.0
                
                failed_tests[test_id] = active_tests.pop(test_id)
                logger.info(f"Test {test_id} timed out after {elapsed:.1f}s and moved to failed_tests")

@app.post("/tests")
async def create_test(test_request: TestRequest):
    test_id = test_request.test_id
    
    print(f"Pinging: {test_request.target_url}")
    ping_result = await ping_backend(test_request.target_url)
    
    if not ping_result["available"]:
        error_msg = f"Backend unavailable: {ping_result['error']}"
        print(f"{error_msg}")
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Backend unavailable",
                "message": error_msg,
                "ping_result": ping_result
            }
        )
    
    print(f"Backend available! Latency: {ping_result['latency_ms']}ms")
    
    try:
        dsl_data = parse_dsl(test_request.dsl_script)
        if not dsl_data.get("steps"):
            raise HTTPException(
                status_code=400, 
                detail="DSL script must contain at least one step"
            )
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid DSL script: {str(e)}"
        )


    test_duration = dsl_data.get("test_duration", 60)
    
    test_status = TestStatus(
        test_id=test_id,
        status="pending",
        progress=0.0,
        start_time=datetime.now(),
        target_url=test_request.target_url,
        dsl_script=test_request.dsl_script,
        auth_credentials=test_request.auth_credentials
    )
    active_tests[test_id] = test_status
    
    
    test_status.test_duration = test_duration

    test_task = {
        "test_id": test_id,
        "target_url": test_request.target_url,
        "dsl_script": test_request.dsl_script,
        "swagger_docs": test_request.swagger_docs,
        "auth_type": test_request.auth_type,
        "auth_credentials": test_request.auth_credentials,
        "created_at": datetime.now().isoformat(),
        "ping_result": ping_result
    }
    
    if test_queue:
        channel = await rabbitmq_connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(test_task).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key="test_tasks"
        )
        
        test_status.status = "running"
        active_tests[test_id] = test_status
        
        return {
            "test_id": test_id, 
            "status": "created", 
            "message": "Test created and sent to workers",
            "backend_status": {
                "available": True,
                "latency_ms": ping_result["latency_ms"],
                "status_code": ping_result["status_code"]
            }
        }
    else:
        raise HTTPException(status_code=500, detail="RabbitMQ unavailable")

@app.post("/ping")
async def ping_backend_endpoint(payload: PingRequest):
    
    ping_result = await ping_backend(payload.url)
    return {
        "url": payload.url,
        "ping_result": ping_result,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/tests/{test_id}")
async def get_test_status(test_id: str):
    if test_id in active_tests:
        test_status = active_tests[test_id]
        
        test_status.progress = calculate_test_progress(test_status)
        return test_status
    
    if test_id in completed_tests:
        return completed_tests[test_id]
    
    if test_id in failed_tests:
        return failed_tests[test_id]
    
    raise HTTPException(status_code=404, detail="Test not found")

@app.get("/tests", response_model=List[TestStatus])
async def list_all_tests():
    
    for test_status in active_tests.values():
        test_status.progress = calculate_test_progress(test_status)
    
    all_tests = list(active_tests.values()) + list(completed_tests.values()) + list(failed_tests.values())
    return all_tests

@app.post("/tests/{test_id}/results")
async def receive_test_results(test_id: str, test_result: Dict[str, Any]):
    try:
        logger.info(f"Received results for test {test_id}: {test_result}")
        
        if test_id in active_tests:
            test_status = active_tests[test_id]  
            
            failed_requests = test_result.get("failed_requests", 0)
            successful_requests = test_result.get("successful_requests", 0)
            
            logger.info(f"Test {test_id}: failed={failed_requests}, successful={successful_requests}")
            
            if failed_requests > successful_requests:
                test_status.status = "failed"
                test_status.end_time = test_result.get("end_time", datetime.now())
                test_status.results = format_test_results(test_result)
                test_status.error = "Test failed: too many failed requests"
                test_status.progress = 100.0
                
                failed_tests[test_id] = active_tests.pop(test_id)
                logger.info(f"Test {test_id} failed and moved to failed_tests")
            else:
                test_status.status = "completed"
                test_status.end_time = test_result.get("end_time", datetime.now())
                test_status.results = format_test_results(test_result)
                test_status.progress = 100.0
                
                completed_tests[test_id] = active_tests.pop(test_id)
                logger.info(f"Test {test_id} completed successfully and moved to completed_tests")
        else:
            logger.warning(f"Test {test_id} not found in active_tests")
            
        return {"message": "Test results received"}
        
    except Exception as e:
        logger.error(f"Error processing test results: {e}")
        raise HTTPException(status_code=500, detail="Error processing results")

@app.post("/tests/{test_id}/progress")
async def receive_progress_update(test_id: str, progress_data: Dict[str, Any]):
    try:
        if test_id in active_tests:
            test_status = active_tests[test_id]
            progress = progress_data.get("progress", 0.0)
            
            if progress > test_status.progress:
                test_status.progress = min(progress, 100.0)
                logger.debug(f"Progress updated for test {test_id}: {progress}%")
            
            return {"message": "Progress update received"}
        else:
            raise HTTPException(status_code=404, detail="Test not found")
            
    except Exception as e:
        logger.error(f"Error processing progress update: {e}")
        raise HTTPException(status_code=500, detail="Error processing progress update")

@app.post("/tests/{test_id}/error")
async def receive_test_error(test_id: str, error_data: Dict[str, Any]):
    try:
        if test_id in active_tests:
            test_status = active_tests[test_id]
            test_status.status = "failed"
            test_status.end_time = datetime.now()
            test_status.error = error_data.get("error", "Unknown error")
            test_status.progress = 100.0
            
            failed_tests[test_id] = active_tests.pop(test_id)
            
            logger.info(f"Test {test_id} marked as failed and moved to failed_tests")
            return {"message": "Error status received"}
        else:
            raise HTTPException(status_code=404, detail="Test not found")
            
    except Exception as e:
        logger.error(f"Error processing test error: {e}")
        raise HTTPException(status_code=500, detail="Error processing error status")

@app.delete("/tests/{test_id}")
async def delete_test(test_id: str):
    if test_id in active_tests:
        del active_tests[test_id]
    if test_id in test_results:
        del test_results[test_id]
    return {"message": "Test deleted"}

@app.post("/generate-dsl", response_model=DSLResponse)
async def generate_dsl(request: GenerateDSLRequest):
    
    try:
        logger.info(f"Generating DSL for description: {request.description[:100]}...")
        
        if not request.swagger_docs and not request.api_endpoints:
            raise HTTPException(
                status_code=400,
                detail="Za generiranje DSL-a iz opisa potrebno je predati ili swagger_docs ili api_endpoints"
            )
        
        result = await llm_service.generate_dsl_from_description(
                    request.description,
                    request.swagger_docs,
                    request.api_endpoints,
                    request.user_model,
                    request.arrival_rate,
                    request.session_duration
                )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate DSL: {result.get('error', 'Unknown error')}"
            )
        
        
        try:
            dsl_data = parse_dsl(result["dsl_script"])
            if not dsl_data.get("steps") and not dsl_data.get("user_journey"):
                raise HTTPException(
                    status_code=400,
                    detail="Generated DSL does not contain any steps or user journeys"
                )
        except Exception as e:
            logger.warning(f"Generated DSL validation failed: {e}")
            
        
        response_data = DSLResponse(
            dsl_script=result["dsl_script"],
            status=result["status"],
            model_used=result.get("model_used"),
            error=result.get("error")
        )
        
        if request.auto_run and request.target_url and result["status"] == "success":
            try:
                test_id = f"auto_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                test_request = {
                    "test_id": test_id,
                    "target_url": request.target_url,
                    "dsl_script": result["dsl_script"],
                    "swagger_docs": None,
                    "auth_credentials": {}
                }
                
                test_status = TestStatus(
                    test_id=test_id,
                    status="pending",
                    progress=0.0,
                    start_time=datetime.now(),
                    target_url=test_request.target_url,
                    dsl_script=test_request.dsl_script,
                    auth_credentials=test_request.auth_credentials
                )
                active_tests[test_id] = test_status
                
                if test_queue:
                    channel = await rabbitmq_connection.channel()
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(test_request).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                        ),
                        routing_key="test_tasks"
                    )
                    test_status.status = "running"
                    active_tests[test_id] = test_status
                    
                    response_data.test_id = test_id
                    response_data.message = "DSL generated and test started automatically"
                else:
                    response_data.message = "DSL generated but test could not be started (RabbitMQ unavailable)"
                    
            except Exception as e:
                logger.error(f"Error in auto-run: {e}")
                response_data.message = f"DSL generated but auto-run failed: {str(e)}"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_dsl endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/optimize-dsl", response_model=DSLResponse)
async def optimize_dsl(request: OptimizeDSLRequest):
    
    try:
        logger.info(f"Optimizing DSL with goal: {request.optimization_goal}")
        try:
            dsl_data = parse_dsl(request.dsl_script)
            if not dsl_data.get("steps") and not dsl_data.get("user_journey"):
                raise HTTPException(
                    status_code=400,
                    detail="Provided DSL does not contain any steps or user journeys"
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid DSL script: {str(e)}"
            )
        
        result = await llm_service.optimize_existing_dsl(
            request.dsl_script, 
            request.optimization_goal
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to optimize DSL: {result.get('error', 'Unknown error')}"
            )
        try:
            optimized_dsl_data = parse_dsl(result["optimized_dsl"])
            if not optimized_dsl_data.get("steps") and not optimized_dsl_data.get("user_journey"):
                logger.warning("Optimized DSL validation failed - returning original")
                return DSLResponse(
                    dsl_script=request.dsl_script,
                    status="warning",
                    model_used=result.get("model_used"),
                    explanation="Optimization failed validation, returning original DSL"
                )
        except Exception as e:
            logger.warning(f"Optimized DSL validation failed: {e}")
            
        
        return DSLResponse(
            dsl_script=result["optimized_dsl"],
            status=result["status"],
            model_used=result.get("model_used"),
            explanation=result.get("explanation"),
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in optimize_dsl endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/validate-dsl")
async def validate_dsl(dsl_script: str = Body(..., media_type="text/plain")):
    
    try:
        dsl_data = parse_dsl(dsl_script)
        
        validation_result = {
            "valid": True,
            "parsed_data": dsl_data,
            "issues": []
        }
        
        
        if not dsl_data.get("steps") and not dsl_data.get("user_journey"):
            validation_result["valid"] = False
            validation_result["issues"].append("DSL must contain at least one step or user journey")
        
        if dsl_data.get("num_users", 0) <= 0:
            validation_result["issues"].append("Number of users should be greater than 0")
        
        if dsl_data.get("test_duration", 0) <= 0:
            validation_result["issues"].append("Test duration should be greater than 0")
        
        return validation_result
        
    except Exception as e:
        return {
            "valid": False,
            "parsed_data": None,
            "issues": [f"DSL parsing error: {str(e)}"]
        }

@app.post("/tests/{test_id}/detailed-report")
async def generate_detailed_report(test_id: str):
    
    try:
        
        if test_id not in completed_tests and test_id not in failed_tests:
            raise HTTPException(status_code=404, detail="Test not found or not completed/failed")
        
        test_status = completed_tests.get(test_id) or failed_tests.get(test_id)
        
        if test_id in test_reports:
            return test_reports[test_id]
        
        
        logger.info(f"Analyzing test data for {test_id}")
        analysis_data = analytics_engine.analyze_test_data(test_status.results)
        
        
        logger.info(f"Generating LLM report for {test_id}")
        report_content = await llm_service.generate_detailed_report(analysis_data)
        
        
        detailed_analysis = DetailedTestAnalysis(
            test_id=test_id,
            test_summary=analysis_data.get("test_summary", {}),
            endpoint_stats=analysis_data.get("endpoint_stats", {}),
            error_patterns=analysis_data.get("error_patterns", []),
            time_series_data=analysis_data.get("time_series_data", {}),
            performance_insights=analysis_data.get("performance_insights", []),
            recommendations=analysis_data.get("recommendations", [])
        )
        
        test_report = TestReport(
            test_id=test_id,
            report_content=report_content,
            analysis_data=detailed_analysis
        )
        
        
        test_reports[test_id] = test_report
        
        logger.info(f"Generated detailed report for {test_id}")
        return test_report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating detailed report for {test_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@app.get("/tests/{test_id}/detailed-report")
async def get_detailed_report(test_id: str):
    
    if test_id not in test_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return test_reports[test_id]

@app.get("/tests/{test_id}/report-content")
async def get_report_content(test_id: str):
    
    if test_id not in test_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "test_id": test_id,
        "content": test_reports[test_id].report_content,
        "generated_at": test_reports[test_id].generated_at.isoformat()
    }

@app.post("/experiments/causal")
async def run_causal_experiment(experiment_request: CausalExperimentRequest):
    """Run a causal inference experiment with multiple test variations"""
    try:
        experiment_id = str(uuid.uuid4())
        
       
        if hasattr(experiment_request, 'generated_variations') and experiment_request.generated_variations:
            variations = experiment_request.generated_variations
        else:
            variations_response = await llm_service.generate_causal_experiment_variations(
                experiment_request.baseline_dsl,
                experiment_request.experiment_description,
                experiment_request.number_of_tests
            )
            
            if variations_response["status"] != "success":
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to generate variations: {variations_response.get('error', 'Unknown error')}"
                )
            
            variations = variations_response["variations"]
        
        
        test_results = []
        test_ids = []
        
        for i, variation in enumerate(variations):
            logger.info(f"Running test {i+1}/{len(variations)} for experiment {experiment_id}")
            
            
            try:
                parsed_dsl = parse_dsl(variation["dsl_script"])
            except Exception as e:
                logger.error(f"Failed to parse DSL for variation {i+1}: {e}")
                continue
            
            
            test_request = TestRequest(
                test_id=str(uuid.uuid4()),
                dsl_script=variation["dsl_script"],
                target_url=experiment_request.target_url,
                auth_type=experiment_request.auth_type,
                auth_credentials=experiment_request.auth_credentials,
                parsed_dsl=parsed_dsl
            )
            
            
            test_id = test_request.test_id
            
            
            ping_result = await ping_backend(test_request.target_url)
            if not ping_result["available"]:
                logger.error(f"Backend unavailable for test {test_id}: {ping_result['error']}")
                continue
            
            
            try:
                dsl_data = parse_dsl(test_request.dsl_script)
                if not dsl_data.get("steps"):
                    logger.error(f"DSL script must contain at least one step for test {test_id}")
                    continue
            except Exception as e:
                logger.error(f"Failed to parse DSL for test {test_id}: {e}")
                continue
            
            
            test_status = TestStatus(
                test_id=test_id,
                status="running",
                progress=0.0,
                start_time=datetime.now(),
                target_url=test_request.target_url,
                dsl_script=test_request.dsl_script,
                auth_credentials=test_request.auth_credentials,
                results={}
            )
            
            
            active_tests[test_id] = test_status
            
            
            try:
                connection = await aio_pika.connect_robust("amqp://localhost")
                channel = await connection.channel()
                
                
                test_task = {
                    "test_id": test_id,
                    "dsl_script": test_request.dsl_script,
                    "parsed_dsl": dsl_data,
                    "target_url": test_request.target_url,
                    "auth_credentials": test_request.auth_credentials,
                    "ping_result": {"available": True, "latency_ms": 0}  
                }
                
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(test_task).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key="test_tasks"  
                )
                
                await connection.close()
                logger.info(f"Test {test_id} sent to workers")
                
            except Exception as e:
                logger.error(f"Failed to send test {test_id} to workers: {e}")
                
                test_status.status = "failed"
                test_status.results = {"error": str(e)}
                failed_tests[test_id] = test_status
                del active_tests[test_id]
                continue
            
            test_ids.append(test_id)
            

            max_wait_time = 60 
            wait_time = 0
            while wait_time < max_wait_time:
                if test_id in completed_tests or test_id in failed_tests:
                    break
                await asyncio.sleep(2)  
                wait_time += 2
            
            
            if test_id in completed_tests:
                test_status = completed_tests[test_id]
                test_result = {
                    "variation_name": variation["variation_name"],
                    "description": variation["description"],
                    "dsl_script": variation["dsl_script"],
                    "test_id": test_id,
                    "status": "completed",
                    "total_requests": test_status.results.get("total_requests", 0),
                    "success_rate": test_status.results.get("success_rate", 0),
                    "avg_latency": test_status.results.get("avg_latency", 0),
                    "failure_rate": test_status.results.get("failure_rate", 0),
                    "error_categories": test_status.results.get("error_categories", {}),
                    "results": test_status.results
                }
            elif test_id in failed_tests:
                test_status = failed_tests[test_id]
                test_result = {
                    "variation_name": variation["variation_name"],
                    "description": variation["description"],
                    "dsl_script": variation["dsl_script"],
                    "test_id": test_id,
                    "status": "failed",
                    "total_requests": test_status.results.get("total_requests", 0),
                    "success_rate": test_status.results.get("success_rate", 0),
                    "avg_latency": test_status.results.get("avg_latency", 0),
                    "failure_rate": test_status.results.get("failure_rate", 0),
                    "error_categories": test_status.results.get("error_categories", {}),
                    "results": test_status.results
                }
            else:
                logger.warning(f"Test {test_id} did not complete within timeout")
                test_result = {
                    "variation_name": variation["variation_name"],
                    "description": variation["description"],
                    "dsl_script": variation["dsl_script"],
                    "test_id": test_id,
                    "status": "timeout",
                    "total_requests": 0,
                    "success_rate": 0,
                    "avg_latency": 0,
                    "failure_rate": 100,
                    "error_categories": {},
                    "results": {}
                }
            
            test_results.append(test_result)
        
        
        logger.info(f"Generating causal analysis for experiment {experiment_id}")
        
        df = causal_analysis_engine.create_experiment_dataframe(test_results)
        
        # Use multi-metric analysis with improved error handling
        causal_results = causal_analysis_engine.analyze_multi_metric_causal_effect(df)
        
        endpoint_analyses = causal_analysis_engine.analyze_multiple_endpoints(df)
        
        combined_causal_results = {
            "overall_analysis": causal_results,
            "endpoint_analyses": endpoint_analyses,
            "dataframe_info": {
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "treatment_groups": df["treatment"].unique().tolist() if "treatment" in df.columns else []
            }
        }
        
        causal_analysis = await causal_analysis_engine.generate_causal_report(
            causal_results, 
            experiment_request.experiment_description
        )
        
        experiment_result = CausalExperimentResult(
            experiment_id=experiment_id,
            baseline_dsl=experiment_request.baseline_dsl,
            generated_variations=variations,
            test_results=test_results,
            causal_analysis=causal_analysis,
            causal_results=combined_causal_results,
            dataframe_info=combined_causal_results.get("dataframe_info", {})
        )
        
        causal_experiments[experiment_id] = experiment_result
        
        logger.info(f"Completed causal experiment {experiment_id}")
        return experiment_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERROR in run_causal_experiment: {e}")
        logger.error(f"❌ Error type: {type(e)}")
        print(f"❌ ERROR in run_causal_experiment: {e}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        logger.error(f"Error running causal experiment: {e}")
        raise HTTPException(status_code=500, detail=f"Error running experiment: {str(e)}")

@app.get("/experiments/{experiment_id}")
async def get_causal_experiment(experiment_id: str):
    """Get causal experiment results"""
    if experiment_id not in causal_experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return causal_experiments[experiment_id]

@app.post("/experiments/generate-variations")
async def generate_causal_variations(experiment_request: CausalExperimentRequest):
    """Generate DSL variations for causal experiment without running tests"""
    try:
        logger.info(f"Generating DSL variations for experiment")
        
        
        variations_response = await llm_service.generate_causal_experiment_variations(
            experiment_request.baseline_dsl,
            experiment_request.experiment_description,
            experiment_request.number_of_tests
        )
        
        if variations_response["status"] != "success":
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate variations: {variations_response.get('error', 'Unknown error')}"
            )
        
        variations = variations_response["variations"]
        logger.info(f"Generated {len(variations)} variations")
        logger.info(f"Variations content: {variations}")
        
        return {
            "variations": variations,
            "status": "success",
            "model_used": variations_response.get("model_used", "unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating variations: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating variations: {str(e)}")

@app.get("/experiments")
async def list_causal_experiments():
    """List all causal experiments"""
    return {
        "experiments": [
            {
                "experiment_id": exp_id,
                "baseline_dsl": exp.baseline_dsl[:100] + "..." if len(exp.baseline_dsl) > 100 else exp.baseline_dsl,
                "generated_at": exp.generated_at,
                "number_of_tests": len(exp.test_results)
            }
            for exp_id, exp in causal_experiments.items()
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
