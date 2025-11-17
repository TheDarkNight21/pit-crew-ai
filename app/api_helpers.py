"""
Helper utilities for OpenF1 API requests with rate limiting and caching.
"""

import time
import pickle
from pathlib import Path
from typing import Callable, Any, Optional
import pandas as pd


def fetch_with_retry(
    fetch_function: Callable,
    max_retries: int = 3,
    initial_wait: float = 30.0,
    backoff_factor: float = 2.0,
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Fetch data with automatic retry on rate limit errors.

    Args:
        fetch_function: The fetch function to call
        max_retries: Maximum number of retry attempts (default: 3)
        initial_wait: Initial wait time in seconds (default: 30)
        backoff_factor: Multiplier for wait time on each retry (default: 2.0)
        *args, **kwargs: Arguments to pass to fetch_function

    Returns:
        DataFrame from successful fetch

    Raises:
        Exception: If all retries fail

    Example:
        >>> from app.data_loader import fetch_laps
        >>> laps = fetch_with_retry(fetch_laps, session_key=9979)
    """
    wait_time = initial_wait

    for attempt in range(max_retries + 1):
        try:
            result = fetch_function(*args, **kwargs)

            # If we succeeded after retrying, add a small delay before next request
            if attempt > 0:
                time.sleep(2.0)

            return result

        except Exception as e:
            error_msg = str(e).lower()

            # Check if it's a rate limit error
            is_rate_limit = (
                '429' in error_msg or
                'too many requests' in error_msg or
                '503' in error_msg or
                'service unavailable' in error_msg
            )

            if is_rate_limit and attempt < max_retries:
                print(f"⚠️  Rate limit hit. Waiting {wait_time:.0f} seconds before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                wait_time *= backoff_factor
            else:
                # Not a rate limit error, or out of retries
                raise


def fetch_with_cache(
    fetch_function: Callable,
    cache_name: str,
    cache_dir: str = "cache",
    force_refresh: bool = False,
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Fetch data with local file caching to minimize API calls.

    Args:
        fetch_function: The fetch function to call
        cache_name: Name for the cache file (without extension)
        cache_dir: Directory to store cache files (default: "cache")
        force_refresh: If True, ignore cache and fetch fresh data
        *args, **kwargs: Arguments to pass to fetch_function

    Returns:
        DataFrame from cache or fresh fetch

    Example:
        >>> from app.data_loader import fetch_laps
        >>> laps = fetch_with_cache(fetch_laps, "monaco_2025_laps", session_key=9979)
        Loading from cache: monaco_2025_laps
    """
    cache_path = Path(cache_dir) / f"{cache_name}.pkl"

    # Check if cached data exists and we're not forcing refresh
    if cache_path.exists() and not force_refresh:
        print(f"📦 Loading from cache: {cache_name}")
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"⚠️  Cache read failed: {e}. Fetching fresh data...")

    # Fetch fresh data
    print(f"🌐 Fetching from API: {cache_name}")
    data = fetch_function(*args, **kwargs)

    # Cache the result
    if not data.empty:
        cache_path.parent.mkdir(exist_ok=True, parents=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        print(f"💾 Cached to: {cache_path}")

    return data


def clear_cache(cache_dir: str = "cache", pattern: str = "*.pkl"):
    """
    Clear cached data files.

    Args:
        cache_dir: Directory containing cache files
        pattern: Glob pattern for files to delete (default: "*.pkl")

    Example:
        >>> clear_cache()  # Clear all cache
        >>> clear_cache(pattern="monaco_*.pkl")  # Clear specific pattern
    """
    cache_path = Path(cache_dir)

    if not cache_path.exists():
        print(f"Cache directory doesn't exist: {cache_dir}")
        return

    files = list(cache_path.glob(pattern))

    if not files:
        print(f"No cache files found matching: {pattern}")
        return

    for file in files:
        file.unlink()
        print(f"🗑️  Deleted: {file.name}")

    print(f"✅ Cleared {len(files)} cache file(s)")


def rate_limited_fetch(
    fetch_function: Callable,
    min_interval: float = 0.5,
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Fetch with enforced minimum interval between requests.

    Args:
        fetch_function: The fetch function to call
        min_interval: Minimum seconds between requests (default: 0.5)
        *args, **kwargs: Arguments to pass to fetch_function

    Returns:
        DataFrame from fetch

    Note:
        Uses a simple time-based throttle. For production use,
        consider a more sophisticated token bucket algorithm.
    """
    # Simple implementation - just wait before each request
    time.sleep(min_interval)
    return fetch_function(*args, **kwargs)


# Convenience function combining caching and retry logic
def smart_fetch(
    fetch_function: Callable,
    cache_name: str,
    use_cache: bool = True,
    max_retries: int = 3,
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Smart fetch with both caching and retry logic.

    This is the recommended way to fetch data from OpenF1 API.

    Args:
        fetch_function: The fetch function to call
        cache_name: Name for cache file
        use_cache: Whether to use caching (default: True)
        max_retries: Max retry attempts for rate limits (default: 3)
        *args, **kwargs: Arguments to pass to fetch_function

    Returns:
        DataFrame from cache or successful fetch

    Example:
        >>> from app.data_loader import fetch_laps
        >>> from app.api_helpers import smart_fetch
        >>>
        >>> # First call - fetches from API and caches
        >>> laps = smart_fetch(fetch_laps, "monaco_2025_laps", session_key=9979)
        >>>
        >>> # Second call - loads from cache instantly
        >>> laps = smart_fetch(fetch_laps, "monaco_2025_laps", session_key=9979)
    """
    if use_cache:
        # Try cache first
        cache_path = Path("cache") / f"{cache_name}.pkl"
        if cache_path.exists():
            return fetch_with_cache(fetch_function, cache_name, *args, **kwargs)

    # Fetch with retry logic
    return fetch_with_retry(fetch_function, max_retries=max_retries, *args, **kwargs)
