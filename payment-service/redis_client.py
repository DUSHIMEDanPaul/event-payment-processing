"""
Redis client — used for idempotency checks.

Each consumed RabbitMQ message has a unique order_id.
Before processing, we check Redis to ensure we haven't
already handled this event (at-least-once delivery guard).
"""

import redis as redis_lib
from config import settings

_client: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    global _client
    if _client is None:
        _client = redis_lib.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
    return _client


def is_already_processed(order_id: str, ttl_seconds: int = 86400) -> bool:
    """Return True if this order_id was already processed (idempotency check)."""
    key = f"payment:processed:{order_id}"
    r = get_redis()
    if r.exists(key):
        return True
    r.setex(key, ttl_seconds, "1")
    return False
