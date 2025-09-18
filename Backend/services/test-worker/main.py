from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
import asyncio
import aio_pika
import aiohttp
import json
import time
import random
from datetime import datetime
import logging
from contextlib import asynccontextmanager
import sys
import os


current_dir = os.path.dirname(os.path.abspath(__file__))
backend_new_dir = os.path.join(current_dir, '..', '..')
sys.path.insert(0, backend_new_dir)

from shared.models import TestTask, TestResult, HealthCheck
from shared.DSL.main import parse_dsl
from modules.journey_executor import execute_user_journey, execute_single_step, execute_with_graceful_degradation, DegradationStrategy
from modules.workload_generator import WorkloadGenerator



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKER_ID = f"worker-{random.randint(1000, 9999)}"
rabbitmq_connection = None
test_queue = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rabbitmq_connection, test_queue
    try:
        rabbitmq_connection = await aio_pika.connect_robust(
            "amqp://guest:guest@localhost/"
        )
        channel = await rabbitmq_connection.channel()
        test_queue = await channel.declare_queue("test_tasks", durable=True)
        
        await start_test_consumer()
        logger.info(f"Worker {WORKER_ID} ready")
    except Exception as e:
        logger.error(f"RabbitMQ connection error: {e}")
    
    yield
    
    if rabbitmq_connection:
        await rabbitmq_connection.close()

app = FastAPI(title="Test Worker", version="1.0.0", lifespan=lifespan)

async def start_test_consumer():
    async def process_message(message):
        async with message.process():
            try:
                test_data = json.loads(message.body.decode())
                logger.info(f"Test received: {test_data['test_id']}")
                
                await run_performance_test(test_data)
                
            except Exception as e:
                logger.error(f"Error processing test: {e}")

    channel = await rabbitmq_connection.channel()
    await channel.set_qos(prefetch_count=1)
    await test_queue.consume(process_message)

async def run_performance_test(test_task: Dict[str, Any]):
    try:
        dsl_script = test_task.get("dsl_script", "")
        dsl_data = parse_dsl(dsl_script)

        test_id = test_task["test_id"]
        target_url = test_task["target_url"]
        num_users = dsl_data.get("num_users", 1)
        test_duration = dsl_data.get("test_duration", 60)
        workload_pattern = dsl_data.get("workload_pattern", "steady")
        user_model = dsl_data.get("user_model", "closed")
        arrival_rate = dsl_data.get("arrival_rate")
        session_duration = dsl_data.get("session_duration")
     
        auth_type = dsl_data.get("auth_type", "none")
        auth_credentials = test_task.get("auth_credentials", {})
        auth_endpoint=auth_credentials.get("loginEndpoint")
        
        timeout = dsl_data.get("timeout", 30)
        retry_attempts = dsl_data.get("retry_attempts", 3)
        
        logger.info(f"Running test {test_id} for {num_users} users with {user_model} model")
        
        start_time = datetime.now()
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        latencies = []
        error_details = []
        
        pattern_config = dsl_data.get("pattern_config", {})
        workload_generator = WorkloadGenerator(
            workload_pattern, num_users, test_duration, pattern_config,
            user_model, arrival_rate, session_duration
        )
        
        progress_update_interval = max(1, test_duration // 10) 
        
        
        if user_model == "open":
            results = await run_open_model_test(test_task, dsl_data, workload_generator, start_time, 
                                              auth_type, auth_credentials, auth_endpoint, timeout, retry_attempts)
        else:
            tasks = []
            for user_id in range(num_users):
                task = simulate_user_journey(
                    user_id, target_url, test_task, workload_generator, start_time,
                    auth_type, auth_credentials, auth_endpoint, timeout, retry_attempts
                )
                tasks.append(task)
            
            progress_task = asyncio.create_task(
                track_progress(test_id, start_time, test_duration, progress_update_interval)
            )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            progress_task.cancel()
        
        for result in results:
            if isinstance(result, dict):
                total_requests += result.get("requests", 0)
                successful_requests += result.get("successful", 0)
                failed_requests += result.get("failed", 0)
                latencies.extend(result.get("latencies", []))
                error_details.extend(result.get("errors", []))
            
        end_time = datetime.now()
        total_latency = sum(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        avg_latency = total_latency / len(latencies) if latencies else 0
        
        test_result = TestResult(
            test_id=test_id,
            worker_id=WORKER_ID,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_latency=total_latency,
            max_latency=max_latency,
            min_latency=min_latency,
            avg_latency=avg_latency,
            error_details=error_details,
            start_time=start_time,
            end_time=end_time
        )
        
        await send_results_to_coordinator(test_result)
        
        logger.info(f"Test {test_id} completed. Success: {successful_requests}, Failed: {failed_requests}")
    except Exception as e:
        logger.error(f"Test {test_id} failed: {e}")
        await send_error_to_coordinator(test_task["test_id"], str(e))

async def run_open_model_test(test_task: Dict[str, Any], dsl_data: Dict[str, Any], 
                             workload_generator: 'WorkloadGenerator', start_time: datetime,
                             auth_type: str = "none", auth_credentials: Dict = None, auth_endpoint: str = None,
                             timeout: int = 30, retry_attempts: int = 3):
    active_users = []
    test_duration = dsl_data.get("test_duration", 60)
    target_url = test_task["target_url"]
    arrival_rate = dsl_data.get("arrival_rate", 1.0)
    
    logger.info(f"Starting open model test:")
    logger.info(f"  - Test duration: {test_duration}s")
    logger.info(f"  - Arrival rate: {arrival_rate} users/second")
    logger.info(f"  - Expected timeout: {test_duration + 60}s")
    
    progress_update_interval = max(1, test_duration // 10)
    progress_task = asyncio.create_task(
        track_progress(test_task["test_id"], start_time, test_duration, progress_update_interval)
    )
    
    try:
        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= test_duration:
                break
            
            arrival_probability = min(arrival_rate * 0.1, 1.0)
            if random.random() < arrival_probability:  
                user_id = len(active_users)
                session_duration = workload_generator.get_session_duration()
                task = asyncio.create_task(
                    simulate_user_session(user_id, target_url, test_task, workload_generator, 
                                        start_time, session_duration, auth_type, auth_credentials, auth_endpoint, timeout, retry_attempts)
                )
                active_users.append(task)
                logger.info(f"Started user session {user_id} (arrival_rate: {arrival_rate}, session_duration: {session_duration:.1f}s, elapsed: {elapsed:.1f}s)")
            
            active_users = [task for task in active_users if not task.done()]
            
            await asyncio.sleep(0.1) 
        
        if active_users:
            logger.info(f"Test duration reached, but {len(active_users)} active sessions still running")
            logger.info("Waiting for active sessions to complete...")
            await asyncio.gather(*active_users, return_exceptions=True)
            logger.info("All active sessions completed")
    
    finally:
        progress_task.cancel()
    
    results = []
    for task in active_users:
        if task.done() and not task.cancelled():
            try:
                result = task.result()
                if isinstance(result, dict):
                    results.append(result)
            except Exception as e:
                logger.error(f"Error in user session: {e}")
    
    return results

async def simulate_user_session(user_id: int, target_url: str, test_task: Dict[str, Any], 
                              workload_generator: 'WorkloadGenerator', start_time: datetime, 
                              session_duration: float, auth_type: str = "none", 
                              auth_credentials: Dict = None, auth_endpoint: str = None,
                              timeout: int = 30, retry_attempts: int = 3):
    requests = [0]
    successful = [0]
    failed = [0]
    latencies = []
    errors = []
    
    dsl_script = test_task.get("dsl_script", "")
    dsl_data = parse_dsl(dsl_script)
    steps = dsl_data.get("steps", [])
    user_journey = dsl_data.get("user_journey", [])
    
    session_start = datetime.now()
    
    async with aiohttp.ClientSession() as session:
        while True:
            elapsed_session = (datetime.now() - session_start).total_seconds()
            if elapsed_session >= session_duration:
                break
            
            elapsed_test = (datetime.now() - start_time).total_seconds()
            workload_generator.update_time(elapsed_test)
            
            delay = workload_generator.get_next_delay()
            if delay > 0:
                await asyncio.sleep(delay)
            
        if user_journey:
            await execute_user_journey(session, target_url, user_journey, 
                                     requests, successful, failed, latencies, errors,
                                     auth_type, auth_credentials, auth_endpoint, timeout, retry_attempts, user_id)
        else:
            endpoint = random.choice(steps)
            strategy = await execute_with_graceful_degradation(
                session, target_url, endpoint, requests, successful, failed, latencies, errors, 
                None, timeout, retry_attempts, user_id
            )
            if strategy == DegradationStrategy.TERMINATE_JOURNEY:
                logger.warning(f"Terminating session for user {user_id} due to critical error")
                return {
                    "requests": requests[0],  
                    "successful": successful[0],  
                    "failed": failed[0],  
                    "latencies": latencies,
                    "errors": errors
                }
    
    return {
        "requests": requests[0],
        "successful": successful[0],
        "failed": failed[0],
        "latencies": latencies,
        "errors": errors
    }

async def simulate_user_journey(user_id: int, target_url: str, test_task: Dict[str, Any], 
                               workload_generator: 'WorkloadGenerator', start_time: datetime,
                               auth_type: str = "none", auth_credentials: Dict = None, auth_endpoint: str = None,
                               timeout: int = 30, retry_attempts: int = 3):
    requests = [0]  
    successful = [0]  
    failed = [0]  
    latencies = []
    errors = []
    
    dsl_script = test_task.get("dsl_script", "")
    dsl_data = parse_dsl(dsl_script)
    steps = dsl_data.get("steps", [])
    user_journey = dsl_data.get("user_journey", [])
    
    async with aiohttp.ClientSession() as session:
        while True:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            workload_generator.update_time(elapsed_time)
            
            if elapsed_time >= dsl_data.get("test_duration", 60):
                break
            
            delay = workload_generator.get_next_delay()
            if delay > 0:
                await asyncio.sleep(delay)

        if user_journey:
            await execute_user_journey(session, target_url, user_journey, 
                                     requests, successful, failed, latencies, errors,
                                     auth_type, auth_credentials, auth_endpoint, timeout, retry_attempts, user_id)
        else:
            endpoint = random.choice(steps)
            strategy = await execute_with_graceful_degradation(
                session, target_url, endpoint, requests, successful, failed, latencies, errors, 
                None, timeout, retry_attempts, user_id
            )
            if strategy == DegradationStrategy.TERMINATE_JOURNEY:
                logger.warning(f"Terminating session for user {user_id} due to critical error")
                return {
                    "requests": requests[0],  
                    "successful": successful[0],  
                    "failed": failed[0],  
                    "latencies": latencies,
                    "errors": errors
                }
    
    return {
        "requests": requests[0],  
        "successful": successful[0],  
        "failed": failed[0],  
        "latencies": latencies,
        "errors": errors
    }




async def send_results_to_coordinator(test_result: TestResult):
    try:
        async with aiohttp.ClientSession() as session:
            coordinator_url = "http://localhost:8001"

            result_data = test_result.model_dump()
            if result_data.get("start_time"):
                result_data["start_time"] = result_data["start_time"].isoformat()
            if result_data.get("end_time"):
                result_data["end_time"] = result_data["end_time"].isoformat()
            
            async with session.post(
                f"{coordinator_url}/tests/{test_result.test_id}/results",
                json=result_data
            ) as response:
                if response.status == 200:
                    logger.info(f"Results sent to coordinator: {test_result.test_id}")
                else:
                    logger.error(f"Error sending results to coordinator: {response.status}")
    except Exception as e:
        logger.error(f"Error sending results to coordinator: {e}")

async def track_progress(test_id: str, start_time: datetime, test_duration: int, update_interval: int):
    try:
        while True:
            await asyncio.sleep(update_interval)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            progress = min((elapsed / test_duration) * 100, 100.0)
            
            await send_progress_update(test_id, progress)
            
            if elapsed >= test_duration:
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in progress tracking: {e}")

async def send_progress_update(test_id: str, progress: float):
    try:
        async with aiohttp.ClientSession() as session:
            coordinator_url = "http://localhost:8001"
            progress_data = {
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            }
            
            async with session.post(
                f"{coordinator_url}/tests/{test_id}/progress",
                json=progress_data
            ) as response:
                if response.status == 200:
                    logger.debug(f"Progress update sent: {progress}%")
                else:
                    logger.error(f"Error sending progress update: {response.status}")
    except Exception as e:
        logger.error(f"Error sending progress update: {e}")

async def send_error_to_coordinator(test_id: str, error_message: str):
    try:
        async with aiohttp.ClientSession() as session:
            coordinator_url = "http://localhost:8001"
            error_data = {
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            }
            
            async with session.post(
                f"{coordinator_url}/tests/{test_id}/error",
                json=error_data
            ) as response:
                if response.status == 200:
                    logger.info(f"Error status sent to coordinator: {test_id}")
                else:
                    logger.error(f"Error sending error status: {response.status}")
    except Exception as e:
        logger.error(f"Error sending error status to coordinator: {e}")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        uptime="active"
    )

@app.get("/stats")
async def get_worker_stats():
    return {
        "worker_id": WORKER_ID,
        "status": "running",
        "uptime": "active",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
