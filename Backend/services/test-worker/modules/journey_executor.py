import time
import aiohttp
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    TIMEOUT = "timeout"
    NETWORK = "network"
    HTTP_ERROR = "http_error"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

def categorize_error(exception: Exception, status_code: int = None):
    if isinstance(exception, asyncio.TimeoutError):
        return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
    elif isinstance(exception, aiohttp.ClientConnectorError):
        return ErrorCategory.NETWORK, ErrorSeverity.HIGH
    elif isinstance(exception, aiohttp.ClientError):
        return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
    elif status_code:
        if status_code == 401:
            return ErrorCategory.AUTH_ERROR, ErrorSeverity.HIGH
        elif status_code == 403:
            return ErrorCategory.AUTH_ERROR, ErrorSeverity.HIGH
        elif 400 <= status_code < 500:
            return ErrorCategory.HTTP_ERROR, ErrorSeverity.MEDIUM
        elif 500 <= status_code < 600:
            return ErrorCategory.SERVER_ERROR, ErrorSeverity.HIGH
    else:
        return ErrorCategory.UNKNOWN, ErrorSeverity.LOW

def create_error_record(category: ErrorCategory, severity: ErrorSeverity, 
                       endpoint: str, user_id: int, attempt: int, 
                       error_msg: str, timestamp: datetime) :
    return {
        "timestamp": timestamp.isoformat(),
        "category": category.value,
        "severity": severity.value,
        "endpoint": endpoint,
        "user_id": user_id,
        "attempt": attempt,
        "error_message": error_msg,
        "retry_eligible": category in [ErrorCategory.TIMEOUT, ErrorCategory.NETWORK, ErrorCategory.SERVER_ERROR]
    }

class DegradationStrategy(Enum):
    SKIP_STEP = "skip_step"
    FALLBACK_ENDPOINT = "fallback_endpoint"
    CONTINUE_JOURNEY = "continue_journey"
    TERMINATE_JOURNEY = "terminate_journey"

def determine_degradation_strategy(category: ErrorCategory, severity: ErrorSeverity, 
                                 attempt: int, max_attempts: int) -> DegradationStrategy:
    if attempt < max_attempts:
        return DegradationStrategy.CONTINUE_JOURNEY
    
    if category == ErrorCategory.AUTH_ERROR:
        return DegradationStrategy.TERMINATE_JOURNEY
    elif category == ErrorCategory.HTTP_ERROR and severity == ErrorSeverity.HIGH:
        return DegradationStrategy.SKIP_STEP
    elif category in [ErrorCategory.TIMEOUT, ErrorCategory.NETWORK]:
        return DegradationStrategy.FALLBACK_ENDPOINT
    else:
        return DegradationStrategy.CONTINUE_JOURNEY

async def execute_with_graceful_degradation(session, target_url: str, endpoint: Dict, 
                                           requests, successful, failed, latencies, errors, 
                                           auth=None, timeout=30, retry_attempts=3, user_id=0):
    method = endpoint.get("method", "GET")
    url = f"{target_url}{endpoint.get('path', '/')}"
    fallback_endpoint = endpoint.get("fallback_endpoint")
    
    
    for attempt in range(retry_attempts + 1):
        try:
            request_start = time.time()
            
            request_params = {}
            if auth:
                if isinstance(auth, dict):  
                    request_params['headers'] = auth
                else:  
                    request_params['auth'] = auth
            
            timeout_config = aiohttp.ClientTimeout(total=timeout)
            request_params['timeout'] = timeout_config
           
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
                return DegradationStrategy.SKIP_STEP
            
            request_end = time.time()
            latency = request_end - request_start
            
            if status_ok:
                requests[0] += 1
                successful[0] += 1
                latencies.append(latency)
                return DegradationStrategy.CONTINUE_JOURNEY
            else:
                requests[0] += 1
                failed[0] += 1
                error_msg = f"HTTP {response.status}: {url} - {response_text[:100]}"
                
                category, severity = categorize_error(None, response.status)
                error_record = create_error_record(category, severity, url, user_id, attempt + 1, error_msg, datetime.now())
                errors.append(error_record)
                
                strategy = determine_degradation_strategy(category, severity, attempt, retry_attempts)
                print(f"DEBUG: Strategy determined: {strategy}, Fallback available: {fallback_endpoint is not None}")
                
                if strategy == DegradationStrategy.FALLBACK_ENDPOINT and fallback_endpoint:
                    logger.info(f"Trying fallback endpoint: {fallback_endpoint}")
                    fallback_url = f"{target_url}{fallback_endpoint}"
                    try:
                        async with session.get(fallback_url, **request_params) as fallback_response:
                            if 200 <= fallback_response.status < 300:
                                requests[0] += 1
                                successful[0] += 1
                                latencies.append(latency)
                                logger.info(f"Fallback endpoint succeeded: {fallback_url}")
                                return DegradationStrategy.CONTINUE_JOURNEY
                    except Exception as e:
                        logger.warning(f"Fallback endpoint also failed: {str(e)}")
                
                return strategy
                
        except asyncio.TimeoutError:
            category, severity = categorize_error(asyncio.TimeoutError(), None)
            error_record = create_error_record(category, severity, url, user_id, attempt + 1, f"Timeout after {timeout}s", datetime.now())
            
            if attempt < retry_attempts:
                logger.warning(f"Timeout on attempt {attempt + 1}/{retry_attempts + 1} for {url}")
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                requests[0] += 1
                failed[0] += 1
                errors.append(error_record)
                strategy = determine_degradation_strategy(category, severity, attempt, retry_attempts)
                return strategy
                
        except Exception as e:
            category, severity = categorize_error(e, None)
            error_record = create_error_record(category, severity, url, user_id, attempt + 1, str(e), datetime.now())
            
            if attempt < retry_attempts and error_record["retry_eligible"]:
                logger.warning(f"Exception on attempt {attempt + 1}/{retry_attempts + 1} for {url}: {str(e)}")
                await asyncio.sleep(1)
                continue
            else:
                requests[0] += 1
                failed[0] += 1
                errors.append(error_record)
                strategy = determine_degradation_strategy(category, severity, attempt, retry_attempts)
                return strategy
    
    return DegradationStrategy.SKIP_STEP

async def execute_user_journey(session, target_url: str, user_journey: List[Dict], 
                              requests, successful, failed, latencies, errors,
                              auth_type: str = "none", auth_credentials: Optional[Dict] = None,
                              auth_endpoint: Optional[str] = None, timeout: int = 30, retry_attempts: int = 3, user_id: int = 0):
    
    auth = await setup_auth(session, target_url, auth_type, auth_credentials, auth_endpoint)
    
    for journey_step in user_journey:
        repeat_count = journey_step.get("repeat", 1)
        for _ in range(repeat_count):
            for step in journey_step["steps"]:
                strategy = await execute_with_graceful_degradation(
                    session, target_url, step, requests, successful, failed, latencies, errors, 
                    auth, timeout, retry_attempts, user_id
                )
                
                if strategy == DegradationStrategy.TERMINATE_JOURNEY:
                    logger.warning(f"Terminating journey for user {user_id} due to critical error")
                    return
                elif strategy == DegradationStrategy.SKIP_STEP:
                    logger.info(f"Skipping step {step.get('path', 'unknown')} for user {user_id}")
                    continue

async def execute_single_step(session, target_url: str, endpoint: Dict, 
                             requests, successful, failed, latencies, errors, auth=None, timeout=30, retry_attempts=3, user_id=0):
    method = endpoint.get("method", "GET")
    url = f"{target_url}{endpoint.get('path', '/')}"
    
    for attempt in range(retry_attempts + 1):
        try:
            request_start = time.time()
            
            request_params = {}
            if auth:
                if isinstance(auth, dict):  
                    request_params['headers'] = auth
                else:  
                    request_params['auth'] = auth
            
            timeout_config = aiohttp.ClientTimeout(total=timeout)
            request_params['timeout'] = timeout_config
           
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
                break  
            else:
                requests[0] += 1
                failed[0] += 1
                error_msg = f"HTTP {response.status}: {url} - {response_text[:100]}"
                    
                category, severity = categorize_error(None, response.status)
                error_record = create_error_record(category, severity, url, user_id, attempt + 1, error_msg, datetime.now())
                errors.append(error_record)
                    
                logger.warning(f"HTTP error {response.status} for {url}: {error_msg}")
                break  
            
        except asyncio.TimeoutError:
            category, severity = categorize_error(asyncio.TimeoutError(), None)
            error_record = create_error_record(category, severity, url, user_id, attempt + 1, f"Timeout after {timeout}s", datetime.now())
            
            if attempt < retry_attempts:
                logger.warning(f"Timeout on attempt {attempt + 1}/{retry_attempts + 1} for {url}")
                await asyncio.sleep(2 ** attempt)  
                continue
            else:
                requests[0] += 1
                failed[0] += 1
                errors.append(error_record)
                logger.error(f"Timeout after {retry_attempts} retries: {url}")
                break
        except Exception as e:
            category, severity = categorize_error(e, None)
            error_record = create_error_record(category, severity, url, user_id, attempt + 1, str(e), datetime.now())
            
            if attempt < retry_attempts and error_record["retry_eligible"]:
                logger.warning(f"Exception on attempt {attempt + 1}/{retry_attempts + 1} for {url}: {str(e)}")
                await asyncio.sleep(1)  
                continue
            else:
                requests[0] += 1
                failed[0] += 1
                errors.append(error_record)
                logger.error(f"Exception after {retry_attempts} retries: {url} - {str(e)}")
                break

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
