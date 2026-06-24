import json
from typing import Any, Optional
from redis.asyncio import Redis, RedisCluster, Sentinel
from app.core.config import settings


class RedisClient:
    def __init__(self):
        self._client: Optional[Redis] = None
        self._cluster: Optional[RedisCluster] = None

    async def connect(self):
        if settings.REDIS_SENTINEL:
            sentinel = Sentinel(
                settings.REDIS_SENTINEL_HOSTS,
                password=settings.REDIS_PASSWORD,
            )
            self._client = sentinel.master_for(settings.REDIS_SENTINEL_MASTER)
        else:
            self._client = await Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_POOL_SIZE,
            )

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def setnx(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self._client:
            return False
        result = await self._client.set(key, json.dumps(value), nx=True, ex=ttl)
        return result is not None

    async def get(self, key: str) -> Optional[Any]:
        data = await self._client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value: Any, ttl: int = settings.CACHE_TTL_DEFAULT):
        await self._client.setex(key, ttl, json.dumps(value))

    async def delete(self, *keys: str):
        await self._client.delete(*keys)

    async def exists(self, key: str) -> bool:
        return await self._client.exists(key)

    async def incr(self, key: str) -> int:
        return await self._client.incr(key)

    async def expire(self, key: str, ttl: int):
        await self._client.expire(key, ttl)

    async def publish(self, channel: str, message: Any):
        await self._client.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str):
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def lpush(self, key: str, *values: Any):
        serialized = [json.dumps(v) for v in values]
        await self._client.lpush(key, *serialized)

    async def rpop(self, key: str) -> Optional[Any]:
        data = await self._client.rpop(key)
        if data:
            return json.loads(data)
        return None

    async def llen(self, key: str) -> int:
        return await self._client.llen(key)

    async def smembers(self, key: str) -> set:
        return await self._client.smembers(key)

    async def sadd(self, key: str, *values: str):
        await self._client.sadd(key, *values)

    async def srem(self, key: str, *values: str):
        await self._client.srem(key, *values)

    async def pipeline(self):
        return await self._client.pipeline()

    async def keys(self, pattern: str) -> list[str]:
        return await self._client.keys(pattern)

    async def scan(self, cursor: int = 0, match: str = "*", count: int = 100):
        return await self._client.scan(cursor=cursor, match=match, count=count)


redis_client = RedisClient()
