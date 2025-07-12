"""Async retry decorator with exponential backoff."""
import asyncio
import functools
from typing import Any, Callable, Optional, Tuple, Type, Union

from structlog.stdlib import BoundLogger

from .logger import get_logger

logger = get_logger(__name__)


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_errors: bool = True,
) -> Callable:
    """Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exceptions to catch and retry
        log_errors: Whether to log retry attempts
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        if log_errors:
                            logger.error(
                                "Max retry attempts reached",
                                function=func.__name__,
                                attempt=attempt + 1,
                                max_attempts=max_attempts,
                                error=str(e),
                            )
                        raise
                    
                    if log_errors:
                        logger.warning(
                            "Retrying after error",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=delay,
                            error=str(e),
                        )
                    
                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class RetryableError(Exception):
    """Base exception for errors that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Base exception for errors that should not trigger a retry."""
    pass


async def retry_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Try primary function, fall back to secondary if it fails.
    
    Args:
        primary_func: Primary async function to try
        fallback_func: Fallback async function if primary fails
        *args: Positional arguments for both functions
        **kwargs: Keyword arguments for both functions
        
    Returns:
        Result from either primary or fallback function
    """
    try:
        return await primary_func(*args, **kwargs)
    except Exception as e:
        logger.warning(
            "Primary function failed, trying fallback",
            primary_func=primary_func.__name__,
            fallback_func=fallback_func.__name__,
            error=str(e),
        )
        return await fallback_func(*args, **kwargs)