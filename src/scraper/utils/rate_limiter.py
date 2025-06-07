# src/scraper/utils/rate_limiter.py
"""
Rate limiting utilities for controlling request frequency.
"""

import time
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from threading import Lock
from functools import wraps


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 1.0
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    burst_size: int = 1
    retry_after_limit: bool = True
    backoff_factor: float = 2.0
    max_retries: int = 3


class RateLimiter:
    """
    Thread-safe rate limiter with multiple time windows and burst support.
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.logger = logging.getLogger(f'{__name__}.RateLimiter')
        
        # Request tracking
        self._lock = Lock()
        self._request_times = deque()
        self._minute_requests = deque()
        self._hour_requests = deque()
        
        # Calculate minimum delay between requests
        self._min_delay = 1.0 / self.config.requests_per_second
        self._last_request_time = 0
        
        # Burst bucket
        self._burst_tokens = self.config.burst_size
        self._last_refill = time.time()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'rate_limited': 0,
            'average_delay': 0
        }
    
    def _refill_burst_tokens(self):
        """Refill burst tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self._last_refill
        
        # Refill tokens based on rate
        tokens_to_add = elapsed * self.config.requests_per_second
        self._burst_tokens = min(
            self.config.burst_size,
            self._burst_tokens + tokens_to_add
        )
        
        self._last_refill = now
    
    def _clean_old_requests(self):
        """Remove old request timestamps"""
        now = time.time()
        
        # Clean per-minute tracking
        if self.config.requests_per_minute:
            minute_ago = now - 60
            while self._minute_requests and self._minute_requests[0] < minute_ago:
                self._minute_requests.popleft()
        
        # Clean per-hour tracking
        if self.config.requests_per_hour:
            hour_ago = now - 3600
            while self._hour_requests and self._hour_requests[0] < hour_ago:
                self._hour_requests.popleft()
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            timeout: Maximum time to wait for permission
            
        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                now = time.time()
                self._clean_old_requests()
                self._refill_burst_tokens()
                
                # Check rate limits
                can_proceed = True
                wait_time = 0
                
                # Check per-second rate
                if self._burst_tokens < 1:
                    # Need to wait for token refill
                    wait_time = max(wait_time, self._min_delay)
                    can_proceed = False
                
                # Check per-minute rate
                if self.config.requests_per_minute:
                    if len(self._minute_requests) >= self.config.requests_per_minute:
                        # Wait until oldest request expires
                        wait_time = max(
                            wait_time,
                            60 - (now - self._minute_requests[0])
                        )
                        can_proceed = False
                
                # Check per-hour rate
                if self.config.requests_per_hour:
                    if len(self._hour_requests) >= self.config.requests_per_hour:
                        # Wait until oldest request expires
                        wait_time = max(
                            wait_time,
                            3600 - (now - self._hour_requests[0])
                        )
                        can_proceed = False
                
                if can_proceed:
                    # Consume a burst token
                    self._burst_tokens -= 1
                    
                    # Record request
                    self._request_times.append(now)
                    self._minute_requests.append(now)
                    self._hour_requests.append(now)
                    
                    # Update stats
                    self.stats['total_requests'] += 1
                    
                    # Calculate average delay
                    if len(self._request_times) > 1:
                        delays = [
                            self._request_times[i] - self._request_times[i-1]
                            for i in range(1, len(self._request_times))
                        ]
                        self.stats['average_delay'] = sum(delays) / len(delays)
                    
                    return True
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed + wait_time > timeout:
                    self.stats['rate_limited'] += 1
                    return False
            
            # Wait before retrying
            self.logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
            time.sleep(min(wait_time, 0.1))  # Check frequently for better responsiveness
    
    def get_current_rates(self) -> Dict[str, float]:
        """Get current request rates"""
        with self._lock:
            now = time.time()
            self._clean_old_requests()
            
            rates = {
                'per_second': len([t for t in self._request_times if now - t < 1]),
                'per_minute': len(self._minute_requests),
                'per_hour': len(self._hour_requests),
                'burst_tokens': self._burst_tokens
            }
            
            return rates
    
    def reset(self):
        """Reset rate limiter state"""
        with self._lock:
            self._request_times.clear()
            self._minute_requests.clear()
            self._hour_requests.clear()
            self._burst_tokens = self.config.burst_size
            self._last_refill = time.time()
    
    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass


class DomainRateLimiter:
    """
    Rate limiter that tracks limits per domain.
    """
    
    def __init__(self, default_config: RateLimitConfig = None):
        self.default_config = default_config or RateLimitConfig()
        self.domain_limiters: Dict[str, RateLimiter] = {}
        self.domain_configs: Dict[str, RateLimitConfig] = {}
        self._lock = Lock()
        self.logger = logging.getLogger(f'{__name__}.DomainRateLimiter')
    
    def set_domain_config(self, domain: str, config: RateLimitConfig):
        """Set specific rate limit configuration for a domain"""
        with self._lock:
            self.domain_configs[domain] = config
            # Reset existing limiter if any
            if domain in self.domain_limiters:
                del self.domain_limiters[domain]
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def get_limiter(self, url: str) -> RateLimiter:
        """Get rate limiter for specific domain"""
        domain = self._get_domain(url)
        
        with self._lock:
            if domain not in self.domain_limiters:
                config = self.domain_configs.get(domain, self.default_config)
                self.domain_limiters[domain] = RateLimiter(config)
            
            return self.domain_limiters[domain]
    
    def acquire(self, url: str, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make request to URL"""
        limiter = self.get_limiter(url)
        return limiter.acquire(timeout)
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all domains"""
        with self._lock:
            return {
                domain: limiter.stats
                for domain, limiter in self.domain_limiters.items()
            }


class AsyncRateLimiter:
    """
    Asynchronous rate limiter for async/await code.
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.logger = logging.getLogger(f'{__name__}.AsyncRateLimiter')
        
        # Async lock
        self._lock = asyncio.Lock()
        self._request_times = deque()
        self._burst_tokens = self.config.burst_size
        self._last_refill = time.time()
    
    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request (async)"""
        start_time = time.time()
        
        while True:
            async with self._lock:
                now = time.time()
                
                # Refill tokens
                elapsed = now - self._last_refill
                tokens_to_add = elapsed * self.config.requests_per_second
                self._burst_tokens = min(
                    self.config.burst_size,
                    self._burst_tokens + tokens_to_add
                )
                self._last_refill = now
                
                # Check if we can proceed
                if self._burst_tokens >= 1:
                    self._burst_tokens -= 1
                    self._request_times.append(now)
                    return True
                
                # Calculate wait time
                wait_time = (1 - self._burst_tokens) / self.config.requests_per_second
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed + wait_time > timeout:
                    return False
            
            # Wait asynchronously
            await asyncio.sleep(min(wait_time, 0.1))
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass


def rate_limit(limiter: RateLimiter):
    """
    Decorator for rate limiting function calls.
    
    Usage:
        limiter = RateLimiter(RateLimitConfig(requests_per_second=2))
        
        @rate_limit(limiter)
        def make_request(url):
            return requests.get(url)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.acquire()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def async_rate_limit(limiter: AsyncRateLimiter):
    """
    Decorator for rate limiting async function calls.
    
    Usage:
        limiter = AsyncRateLimiter(RateLimitConfig(requests_per_second=2))
        
        @async_rate_limit(limiter)
        async def make_request(url):
            return await aiohttp.get(url)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Preset configurations for common scenarios
RATE_LIMIT_PRESETS = {
    'conservative': RateLimitConfig(
        requests_per_second=0.5,
        requests_per_minute=20,
        burst_size=2
    ),
    'moderate': RateLimitConfig(
        requests_per_second=1.0,
        requests_per_minute=50,
        burst_size=5
    ),
    'aggressive': RateLimitConfig(
        requests_per_second=5.0,
        requests_per_minute=200,
        burst_size=10
    ),
    'respectful_bot': RateLimitConfig(
        requests_per_second=0.2,
        requests_per_minute=10,
        requests_per_hour=500,
        burst_size=1
    )
}