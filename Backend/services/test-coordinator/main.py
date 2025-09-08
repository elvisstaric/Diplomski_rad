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


from shared.models import PingRequest, TestRequest, TestStatus, BaseResponse, ErrorResponse
from shared.DSL.main import parse_dsl
from modules.utils import ping_backend, calculate_test_progress, format_test_results

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




async def check_test_timeouts():
    current_time = datetime.now()
    for test_id, test_status in list(active_tests.items()):
        if test_status.start_time and test_status.test_duration:
            elapsed = (current_time - test_status.start_time).total_seconds()
            
            test_status.progress = calculate_test_progress(test_status)
            
            if elapsed > test_status.test_duration:
                test_status.status = "failed"
                test_status.end_time = current_time
                test_status.error = "Test timeout"
                test_status.progress = 100.0
                
                failed_tests[test_id] = active_tests.pop(test_id)
                logger.info(f"Test {test_id} timed out and moved to failed_tests")

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
        start_time=datetime.now()
    )
    active_tests[test_id] = test_status
    
    
    test_status.test_duration = test_duration

    test_task = {
        "test_id": test_id,
        "target_url": test_request.target_url,
        "dsl_script": test_request.dsl_script,
        "swagger_docs": test_request.swagger_docs,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
