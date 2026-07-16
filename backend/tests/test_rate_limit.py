from app.core.rate_limit import InMemoryRateLimiter


def test_in_memory_rate_limiter_blocks_above_limit() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.allow("client", limit=2, window_seconds=60) is True
    assert limiter.allow("client", limit=2, window_seconds=60) is True
    assert limiter.allow("client", limit=2, window_seconds=60) is False
