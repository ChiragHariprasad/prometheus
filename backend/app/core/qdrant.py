from typing import Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance
from app.core.config import settings
from app.core.logging import logger


class QdrantClientWrapper:
    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None

    async def connect(self):
        kwargs = {
            "host": settings.QDRANT_HOST,
            "port": settings.QDRANT_PORT,
            "grpc_port": settings.QDRANT_GRPC_PORT,
            "prefer_grpc": settings.QDRANT_PREFER_GRPC,
            "timeout": settings.QDRANT_TIMEOUT,
        }
        if settings.QDRANT_API_KEY:
            kwargs["api_key"] = settings.QDRANT_API_KEY
        self._client = AsyncQdrantClient(**kwargs)

        await self._ensure_collections()
        logger.info("Qdrant client connected")

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def _ensure_collections(self):
        collections = [
            "customer_embeddings", "customer_interests",
            "product_embeddings", "campaign_embeddings", "semantic_memory",
        ]
        for name in collections:
            try:
                await self._client.get_collection(name)
            except Exception:
                await self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
                    shard_number=6,
                    replication_factor=2,
                )
                logger.info(f"Created Qdrant collection: {name}")

    @property
    def client(self) -> AsyncQdrantClient:
        if not self._client:
            raise RuntimeError("Qdrant client not connected")
        return self._client

    async def upsert(self, collection_name: str, points: list):
        await self.client.upsert(collection_name, points)

    async def search(self, collection_name: str, **kwargs):
        return await self.client.search(collection_name, **kwargs)

    async def scroll(self, collection_name: str, **kwargs):
        return await self.client.scroll(collection_name, **kwargs)

    async def delete(self, collection_name: str, **kwargs):
        await self.client.delete(collection_name, **kwargs)

    async def count(self, collection_name: str, **kwargs):
        return await self.client.count(collection_name, **kwargs)

    async def update_collection(self, collection_name: str, **kwargs):
        await self.client.update_collection(collection_name, **kwargs)

    async def create_payload_index(self, collection_name: str, field_name: str, field_type: str):
        await self.client.create_payload_index(
            collection_name, field_name, field_type
        )


qdrant_client = QdrantClientWrapper()
