import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis import redis_client
from app.core.config import settings


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

        pipe = await redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, period)
        results = await pipe.execute()
        current = results[0]

        if current > max_requests:
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": f"Rate limit exceeded: {limit}"},
                headers={"Retry-After": str(period)},
            )

        return await call_next(request)

    def _parse_rate_limit(self, limit: str) -> tuple[int, int]:
        count, period = limit.split("/")
        period_seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
        return int(count), period_seconds.get(period, 60)

    def _excluded_paths(self) -> set:
        return {"/health", "/ready", "/metrics"}
