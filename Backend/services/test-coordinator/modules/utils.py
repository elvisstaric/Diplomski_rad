import time
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

async def ping_backend(url: str, timeout: int = 10):
    try:
        if not url.startswith(('http://', 'https://')):
            url = f"http://{url}"
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True
            ) as response:
                end_time = time.time()
                latency = (end_time - start_time) * 1000 
                
                return {
                    "available": True,
                    "status_code": response.status,
                    "latency_ms": round(latency, 2),
                    "response_time": response.headers.get("X-Response-Time", "N/A"),
                    "server": response.headers.get("Server", "Unknown"),
                    "url": str(response.url)
                }
                
    except asyncio.TimeoutError:
        return {
            "available": False,
            "error": "Timeout",
            "timeout": timeout
        }
    except aiohttp.ClientConnectorError as e:
        return {
            "available": False,
            "error": f"Connection error - {str(e)}",
            "details": "Backend unavailable"
        }
    except Exception as e:
        return {
            "available": False,
            "error": f"Unexpected error - {str(e)}",
            "details": "Unknown error"
        }

def calculate_test_progress(test_status):
    if not test_status.start_time or not test_status.test_duration:
        return 0.0
    
    current_time = datetime.now()
    elapsed = (current_time - test_status.start_time).total_seconds()
    progress = min((elapsed / test_status.test_duration) * 100, 100.0)
    
    return round(progress, 2)

def format_test_results(test_result: Dict[str, Any]):
    total_requests = test_result.get("total_requests", 0)
    successful_requests = test_result.get("successful_requests", 0)
    failed_requests = test_result.get("failed_requests", 0)
    
    return {
        "test_id": test_result.get("test_id"),
        "worker_id": test_result.get("worker_id"),
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "total_latency": test_result.get("total_latency", 0.0),
        "max_latency": test_result.get("max_latency", 0.0),
        "min_latency": test_result.get("min_latency", 0.0),
        "avg_latency": test_result.get("avg_latency", 0.0),
        "latency_variance": test_result.get("latency_variance", 0.0),
        "success_rate": round((successful_requests / max(total_requests, 1)) * 100, 2),
        "failure_rate": round((failed_requests / max(total_requests, 1)) * 100, 2),
        "error_details": test_result.get("error_details", []),
        "start_time": test_result.get("start_time"),
        "end_time": test_result.get("end_time")
    }
