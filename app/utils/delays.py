"""
Human-like Delays System
Gaussian distribution + exponential backoff with jitter
"""
import random
import time
from typing import Optional


def gaussian_delay(min_seconds: float, max_seconds: float) -> float:
    """
    Generate human-like delay using Gaussian distribution
    
    Args:
        min_seconds: Minimum delay
        max_seconds: Maximum delay
        
    Returns:
        Delay in seconds following normal distribution
    """
    mean = (min_seconds + max_seconds) / 2
    std_dev = (max_seconds - min_seconds) / 6  # 99.7% within range
    
    delay = random.gauss(mean, std_dev)
    delay = max(min_seconds, min(max_seconds, delay))  # Clamp to range
    
    return delay


def page_load_delay():
    """Simulate realistic page load time (1.5-4.0s)"""
    delay = gaussian_delay(1.5, 4.0)
    time.sleep(delay)
    return delay


def click_delay():
    """Simulate realistic click delay (0.3-1.2s)"""
    delay = gaussian_delay(0.3, 1.2)
    time.sleep(delay)
    return delay


def scroll_delay():
    """Simulate realistic scroll delay (0.5-1.5s)"""
    delay = gaussian_delay(0.5, 1.5)
    time.sleep(delay)
    return delay


def search_delay():
    """Delay between searches (2.0-5.0s)"""
    delay = gaussian_delay(2.0, 5.0)
    time.sleep(delay)
    return delay


def exponential_backoff(
    attempt: int,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    Exponential backoff with optional jitter
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Add randomness (±25%)
        
    Returns:
        Delay in seconds
    """
    # Calculate exponential delay: base * 2^attempt
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    # Add jitter (±25% randomness)
    if jitter:
        jitter_amount = delay * 0.25
        delay += random.uniform(-jitter_amount, jitter_amount)
    
    # Ensure non-negative
    delay = max(0, delay)
    
    time.sleep(delay)
    return delay


def retry_with_backoff(
    func,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry function with exponential backoff
    
    Args:
        func: Function to retry
        max_attempts: Maximum retry attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay cap
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Function result
        
    Raises:
        Last exception if all attempts fail
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            
            if attempt < max_attempts - 1:  # Not last attempt
                delay = exponential_backoff(
                    attempt,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    jitter=True
                )
                print(f"  ⚠ Retry {attempt + 1}/{max_attempts - 1} after {delay:.1f}s")
            else:
                print(f"  ✗ Max retries reached")
    
    # All attempts failed
    raise last_exception
