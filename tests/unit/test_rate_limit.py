import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from apps.api.app.core.rate_limit import RateLimiter
from apps.api.app.core.errors import APIError


@pytest.mark.asyncio
async def test_rate_limiter_memory_fallback():
    limiter = RateLimiter(times=2, seconds=10)

    # Build dummy request
    request = MagicMock(spec=Request)
    request.client = MagicMock()
    request.client.host = "192.168.1.100"
    request.state = MagicMock()
    request.state.user = None

    # First request: ok
    await limiter(request)

    # Second request: ok
    await limiter(request)

    # Third request: should trigger APIError 429
    with pytest.raises(APIError) as exc_info:
        await limiter(request)
    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"
    assert exc_info.value.details["limit"] == 2
