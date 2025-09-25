"""
Retry utilities for batch processing.
Provides exponential backoff retry logic for LLM and MongoDB operations.
"""

import asyncio
import random
import time
from functools import wraps
from typing import Callable, TypeVar, Any, Optional, List, Dict
from logger import logger

# Type variable for generic function return type
T = TypeVar('T')

class RetryError(Exception):
    """Exception raised when retries are exhausted."""
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        self.message = message
        self.last_exception = last_exception
        super().__init__(f"{message}. Original exception: {last_exception}" if last_exception else message)

def classify_error(exc: Exception) -> str:
    """
    Classify the error type to determine retry strategy.
    
    Args:
        exc: The exception to classify
        
    Returns:
        String indicating error type: "transient", "resource", or "permanent"
    """
    error_str = str(exc).lower()
    
    # Network/connection related errors
    if any(term in error_str for term in ["timeout", "connection", "network", "refused", "unavailable"]):
        return "transient"
    
    # Resource limitations
    if any(term in error_str for term in ["rate limit", "too many requests", "quota", "capacity", "overloaded"]):
        return "resource"
    
    # Authentication/authorization errors are permanent
    if any(term in error_str for term in ["authentication", "unauthorized", "forbidden", "auth", "permission"]):
        return "permanent"
    
    # Invalid requests are permanent errors
    if any(term in error_str for term in ["bad request", "invalid", "not found", "syntax error"]):
        return "permanent"
        
    # Default to transient for unknown errors
    return "transient"

async def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: float = 0.1,
    error_types: List[str] = ["transient", "resource"],
    **kwargs: Any
) -> T:
    """
    Execute a function with exponential backoff retry logic.
    
    Args:
        func: The async function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Random jitter factor (0-1) to add to delay
        error_types: Types of errors to retry ("transient", "resource", "permanent")
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function call
        
    Raises:
        RetryError: When all retries are exhausted
    """
    attempts = 0
    last_exception = None
    
    while attempts <= max_retries:
        try:
            if attempts > 0:
                logger.info(f"Retry attempt {attempts}/{max_retries}...")
                
            return await func(*args, **kwargs)
            
        except Exception as e:
            attempts += 1
            last_exception = e
            
            # Check if we should retry based on the error type
            error_type = classify_error(e)
            if error_type not in error_types:
                logger.warning(f"Not retrying due to permanent error: {e}")
                raise
                
            # Check if we've exhausted retries
            if attempts > max_retries:
                logger.error(f"Failed after {max_retries} retry attempts: {e}")
                break
                
            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (2 ** (attempts - 1)), max_delay)
            # Add jitter to avoid thundering herd problem
            jitter_amount = random.uniform(-jitter * delay, jitter * delay)
            delay = max(0.1, delay + jitter_amount)
            
            logger.info(f"Error: {e}. Retrying in {delay:.2f} seconds... (Attempt {attempts}/{max_retries})")
            await asyncio.sleep(delay)
    
    raise RetryError(f"Failed after {max_retries} retry attempts", last_exception)

def async_retry(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: float = 0.1,
    error_types: List[str] = ["transient", "resource"]
) -> Callable:
    """
    Decorator for async functions to add retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Random jitter factor (0-1) to add to delay
        error_types: Types of errors to retry ("transient", "resource", "permanent")
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_with_backoff(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter,
                error_types=error_types,
                **kwargs
            )
        return wrapper
    return decorator