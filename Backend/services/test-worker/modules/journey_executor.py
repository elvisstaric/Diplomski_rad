import time
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

async def execute_user_journey(session, target_url: str, user_journey: List[Dict], 
                              requests, successful, failed, latencies, errors,
                              auth_type: str = "none", auth_credentials: Optional[Dict] = None,
                              auth_endpoint: Optional[str] = None):
    
    auth = await setup_auth(session, target_url, auth_type, auth_credentials, auth_endpoint)
    
    for journey_step in user_journey:
        repeat_count = journey_step.get("repeat", 1)
        for _ in range(repeat_count):
            for step in journey_step["steps"]:
                await execute_single_step(session, target_url, step, 
                                        requests, successful, failed, latencies, errors, auth)

async def execute_single_step(session, target_url: str, endpoint: Dict, 
                             requests, successful, failed, latencies, errors, auth=None):
    method = endpoint.get("method", "GET")
    url = f"{target_url}{endpoint.get('path', '/')}"
    
    try:
        request_start = time.time()
        
        request_params = {}
        if auth:
            if isinstance(auth, dict):  
                request_params['headers'] = auth
            else:  
                request_params['auth'] = auth
       
        if method == "GET":
            async with session.get(url, **request_params) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "POST":
            payload = endpoint.get("payload", {})
            async with session.post(url, json=payload, **request_params) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "PUT":
            payload = endpoint.get("payload", {})
            async with session.put(url, json=payload, **request_params) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "PATCH":
            payload = endpoint.get("payload", {})
            async with session.patch(url, json=payload, **request_params) as response:
                response_text = await response.text()
                status_ok = 200 <= response.status < 300
        elif method == "DELETE":
            async with session.delete(url, **request_params) as response:
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
            errors.append(f"HTTP {response.status}: {url} - {response_text[:100]}")
        
    except Exception as e:
        requests[0] += 1
        failed[0] += 1
        errors.append(f"Exception: {url} - {str(e)}")

async def setup_auth(session, target_url: str, auth_type: str, auth_credentials: Optional[Dict], auth_endpoint: Optional[str]):
    
    
    if auth_type == "none" or not auth_credentials:
        return None
    
    if auth_type == "basic":
        username = auth_credentials.get('username')
        password = auth_credentials.get('password')
        if username and password:
            return aiohttp.BasicAuth(username, password)
        return None
    
    elif auth_type == "bearer":
        token = auth_credentials.get('token')
        if token:
            return {"Authorization": f"Bearer {token}"}
        return None
    
    elif auth_type == "session":
        username = auth_credentials.get('username')
        password = auth_credentials.get('password')
        if username and password:
           
            login_endpoint = auth_endpoint or '/login'
            login_data = {
                'username': username,
                'password': password
            }
            
            try:
                async with session.post(f"{target_url}{login_endpoint}", json=login_data) as response:
                    if response.status == 200:
                        logger.info(f"Successfully authenticated user: {username}")
                        return None  
                    else:
                        logger.warning(f"Login failed for user {username}: HTTP {response.status}" )
                        return None
            except Exception as e:
                logger.error(f"Login error for user {username}: {str(e)}")
                return None
        return None
    
    return None
