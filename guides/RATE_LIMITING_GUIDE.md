# OpenF1 API Rate Limiting Guide

## Quick Answer

**If you hit a rate limit:**
- **First retry:** Wait **30 seconds**
- **Second retry:** Wait **60 seconds**
- **Third retry:** Wait **5 minutes**

## Best Practices

### 1. Use Caching (Recommended!)

The best way to avoid rate limits is to cache your results:

```python
from app.api_helpers import smart_fetch
from app.data_loader import fetch_laps

# First call - fetches from API
laps = smart_fetch(fetch_laps, "monaco_2025_laps", session_key=9979)

# Second call - instant from cache!
laps = smart_fetch(fetch_laps, "monaco_2025_laps", session_key=9979)
```

### 2. Run the Caching Example

```bash
python example_scripts/example_with_caching.py
```

This will:
- ✅ Cache all API responses locally
- ✅ Automatically retry on rate limits with exponential backoff
- ✅ Skip API calls on subsequent runs (instant!)

### 3. Clear Cache When Needed

```bash
# Clear all cache
python -c "from app.api_helpers import clear_cache; clear_cache()"

# Clear specific session
python -c "from app.api_helpers import clear_cache; clear_cache(pattern='monaco_*.pkl')"
```

---

## Rate Limit Strategies

### Strategy 1: Smart Fetch (Easiest)

```python
from app.api_helpers import smart_fetch
from app.data_loader import fetch_laps

# Automatically handles caching + retries
laps = smart_fetch(fetch_laps, "my_cache_name", session_key=9979)
```

**Benefits:**
- Automatic caching
- Automatic retry with exponential backoff
- One-line solution

### Strategy 2: Manual Caching

```python
from app.api_helpers import fetch_with_cache
from app.data_loader import fetch_laps

laps = fetch_with_cache(fetch_laps, "laps_cache", session_key=9979)
```

**Benefits:**
- Full control over cache
- Can force refresh with `force_refresh=True`

### Strategy 3: Retry Only

```python
from app.api_helpers import fetch_with_retry
from app.data_loader import fetch_laps

laps = fetch_with_retry(fetch_laps, max_retries=3, session_key=9979)
```

**Benefits:**
- No caching (always fresh data)
- Automatic retry on rate limits

### Strategy 4: Rate Limiting

```python
from app.api_helpers import rate_limited_fetch
from app.data_loader import fetch_laps

# Enforces 500ms between requests
laps = rate_limited_fetch(fetch_laps, min_interval=0.5, session_key=9979)
```

**Benefits:**
- Prevents hitting rate limits in first place
- Good for batch processing

---

## Understanding Rate Limits

### What Triggers Rate Limits?

1. **Too many requests in short time** - Making 10+ requests per second
2. **Large data pulls** - Fetching car_data for entire races (100k+ rows)
3. **Repeated identical requests** - Not using caching

### HTTP Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 429 | Too Many Requests | Wait 30s, then retry |
| 503 | Service Unavailable | Wait 60s, API may be overloaded |
| 422 | Unprocessable Entity | Data not available for this session |

### Typical Limits (Estimated)

OpenF1 doesn't publish official limits, but based on testing:

- **Likely safe:** 2-3 requests per second
- **Conservative:** 1 request per second
- **Very safe:** 1 request every 2 seconds

---

## Advanced: Batch Processing

If processing multiple races, use this pattern:

```python
from app.api_helpers import smart_fetch
from app.data_loader import fetch_laps
import time

races = [
    ("Monaco", 2025, 9979),
    ("Spain", 2025, 9980),
    ("Canada", 2025, 9981),
]

for country, year, session_key in races:
    cache_name = f"{country.lower()}_{year}_laps"

    print(f"Processing {country} {year}...")
    laps = smart_fetch(fetch_laps, cache_name, session_key=session_key)

    # Small delay between races (if not cached)
    time.sleep(1.0)
```

**This pattern:**
- Uses caching (instant for already-processed races)
- Adds delays between API calls
- Won't fail if one race hits rate limit

---

## Troubleshooting

### "Too many requests" error

```python
# Solution 1: Use smart_fetch (handles retries)
from app.api_helpers import smart_fetch
data = smart_fetch(fetch_function, "cache_name", session_key=session_key)

# Solution 2: Manual retry with longer wait
from app.api_helpers import fetch_with_retry
data = fetch_with_retry(
    fetch_function,
    max_retries=5,
    initial_wait=60.0,  # Start with 60s
    backoff_factor=2.0,
    session_key=session_key
)
```

### Cache taking up too much space

```python
# Check cache size
import os
from pathlib import Path

cache_dir = Path("cache")
total_size = sum(f.stat().st_size for f in cache_dir.glob("*.pkl"))
print(f"Cache size: {total_size / 1024 / 1024:.1f} MB")

# Clear old cache files
from app.api_helpers import clear_cache
clear_cache(pattern="2023_*.pkl")  # Clear old year
```

### Need fresh data

```python
# Force refresh (ignore cache)
from app.api_helpers import fetch_with_cache
data = fetch_with_cache(
    fetch_function,
    "cache_name",
    force_refresh=True,  # Ignore cache
    session_key=session_key
)
```

---

## Summary

**Best Practice for Most Users:**

```python
from app.api_helpers import smart_fetch

# Use this for everything!
data = smart_fetch(fetch_function, "unique_cache_name", session_key=session_key)
```

This gives you:
- ✅ Automatic caching (instant subsequent loads)
- ✅ Automatic retry on rate limits
- ✅ Exponential backoff (30s → 60s → 5min)
- ✅ No manual error handling needed

**Run the caching example:**
```bash
python example_scripts/example_with_caching.py
```

First run fetches from API. Second run is instant from cache! 🚀
