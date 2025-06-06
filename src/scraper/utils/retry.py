# src/scraper/utils/retry.py
"""
Retry mechanisms and decorators for robust error handling.
"""

import time
import logging
from functools import wraps
from typing import Tuple, Type, Callable, Any, Optional, Union

from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)


# Default exceptions to retry on
DEFAULT_RETRY_EXCEPTIONS = (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    WebDriverException
)

# Exceptions that should not be retried
NO_RETRY_EXCEPTIONS = (
    KeyboardInterrupt,
    SystemExit,
    MemoryError
)


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 2.0,
    backoff: float = 1.5,
    exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRY_EXCEPTIONS,
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    Decorator for retrying functions on specific exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for exponential delay
        exceptions: Tuple of exceptions to retry on
        logger: Logger instance for logging retry attempts
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except NO_RETRY_EXCEPTIONS:
                    # Don't retry on these exceptions
                    raise
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for "
                        f"{func.__name__}: {type(e).__name__}: {str(e)}"
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
                except Exception as e:
                    # Unexpected exception, log and re-raise
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def retry_with_refresh(
    driver,
    func: Callable,
    max_retries: int = 3,
    refresh_on_exceptions: Tuple[Type[Exception], ...] = (StaleElementReferenceException,)
) -> Any:
    """
    Retry function with page refresh on specific exceptions.
    
    Args:
        driver: Selenium WebDriver instance
        func: Function to retry
        max_retries: Maximum number of retries
        refresh_on_exceptions: Exceptions that trigger page refresh
        
    Returns:
        Function return value
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries + 1):
        try:
            return func()
            
        except refresh_on_exceptions as e:
            if attempt == max_retries:
                logger.error(f"Max retries reached with refresh: {e}")
                raise
            
            logger.warning(f"Refreshing page due to {type(e).__name__}, attempt {attempt + 1}")
            driver.refresh()
            time.sleep(2)  # Wait for page to load
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise


def wait_and_retry(
    condition_func: Callable[[], bool],
    timeout: float = 30.0,
    poll_interval: float = 0.5,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """
    Wait for a condition to be true with polling.
    
    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between condition checks
        error_message: Error message if timeout occurs
        
    Returns:
        True if condition met, raises TimeoutException otherwise
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if condition_func():
                return True
        except Exception:
            # Ignore exceptions in condition check
            pass
        
        time.sleep(poll_interval)
    
    raise TimeoutException(error_message)


class RetryContext:
    """Context manager for retry logic with state tracking"""
    
    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRY_EXCEPTIONS,
        logger: Optional[logging.Logger] = None
    ):
        self.max_retries = max_retries
        self.delay = delay
        self.exceptions = exceptions
        self.logger = logger or logging.getLogger(__name__)
        self.attempts = 0
        self.last_exception = None
    
    def __enter__(self):
        self.attempts = 0
        self.last_exception = None
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True
        
        if exc_type in NO_RETRY_EXCEPTIONS:
            return False
        
        if exc_type in self.exceptions and self.attempts < self.max_retries:
            self.attempts += 1
            self.last_exception = exc_val
            self.logger.warning(
                f"Retry {self.attempts}/{self.max_retries}: "
                f"{exc_type.__name__}: {exc_val}"
            )
            time.sleep(self.delay)
            return True
        
        return False
    
    def should_retry(self) -> bool:
        """Check if more retries are available"""
        return self.attempts < self.max_retries


def exponential_backoff(
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    factor: float = 2.0
) -> Callable[[int], float]:
    """
    Create exponential backoff delay function.
    
    Args:
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        factor: Multiplication factor for each retry
        
    Returns:
        Function that calculates delay for given attempt number
    """
    def calculate_delay(attempt: int) -> float:
        delay = initial_delay * (factor ** attempt)
        return min(delay, max_delay)
    
    return calculate_delay


def retry_on_stale_element(func: Callable) -> Callable:
    """
    Decorator specifically for handling stale element references.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except StaleElementReferenceException:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(0.5)
        
    return wrapper


def is_retriable_exception(exception: Exception) -> bool:
    """
    Check if an exception should be retried.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if exception should be retried
    """
    # Don't retry on critical exceptions
    if isinstance(exception, NO_RETRY_EXCEPTIONS):
        return False
    
    # Check if it's a known retriable exception
    if isinstance(exception, DEFAULT_RETRY_EXCEPTIONS):
        return True
    
    # Check for specific error messages that indicate retriable conditions
    error_message = str(exception).lower()
    retriable_messages = [
        'timeout',
        'not clickable',
        'obscured',
        'not interactable',
        'stale element',
        'no such element',
        'connection refused',
        'connection reset'
    ]
    
    return any(msg in error_message for msg in retriable_messages)