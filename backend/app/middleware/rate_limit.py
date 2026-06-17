import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis import redis_client
from app.core.config import settings
from app.core.exceptions import RateLimitException


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        if request.url.path in self._excluded_paths():
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if path.startswith("/api/v1/auth/"):
            limit = settings.RATE_LIMIT_AUTH
        elif path.startswith("/api/v1/events/"):
            limit = settings.RATE_LIMIT_EVENTS
        else:
            limit = settings.RATE_LIMIT_DEFAULT

        max_requests, period = self._parse_rate_limit(limit)
        key = f"ratelimit:{client_ip}:{path}"

        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, period)

        if current > max_requests:
            raise RateLimitException(f"Rate limit exceeded: {limit}")

        return await call_next(request)

    def _parse_rate_limit(self, limit: str) -> tuple[int, int]:
        count, period = limit.split("/")
        period_seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
        return int(count), period_seconds.get(period, 60)

    def _excluded_paths(self) -> set:
        return {"/health", "/ready", "/metrics"}
