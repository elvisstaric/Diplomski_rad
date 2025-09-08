import time
import aiohttp
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

async def execute_user_journey(session, target_url: str, user_journey: List[Dict], 
                              requests, successful, failed, latencies, errors):
    for journey_step in user_journey:
        repeat_count = journey_step.get("repeat", 1)
        for _ in range(repeat_count):
            for step in journey_step["steps"]:
                await execute_single_step(session, target_url, step, 
                                        requests, successful, failed, latencies, errors)

async def execute_single_step(session, target_url: str, endpoint: Dict, 
                             requests, successful, failed, latencies, errors):
    method = endpoint.get("method", "GET")
    url = f"{target_url}{endpoint.get('path', '/')}"
    
    try:
        request_start = time.time()
       
        if method == "GET":
            async with session.get(url) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "POST":
            payload = endpoint.get("payload", {})
            async with session.post(url, json=payload) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "PUT":
            payload = endpoint.get("payload", {})
            async with session.put(url, json=payload) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "PATCH":
            payload = endpoint.get("payload", {})
            async with session.patch(url, json=payload) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "DELETE":
            async with session.delete(url) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        else:
            logger.warning(f"Unsupported HTTP method: {method} for endpoint: {url}")
            return
        
        request_end = time.time()
        latency = request_end - request_start
        
        if status_ok:
            requests[0] += 1
            successful[0] += 1
            latencies.append(latency)
        else:
            requests[0] += 1
            failed[0] += 1
            errors.append({
                "endpoint": url,
                "status_code": response.status,
                "error": response_text[:100]
            })
        
    except Exception as e:
        requests[0] += 1
        failed[0] += 1
        errors.append({
            "endpoint": url,
            "status_code": None,
            "error": str(e)
        })
