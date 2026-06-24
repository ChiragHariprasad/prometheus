import json
import asyncio
from typing import Callable, Awaitable, Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.logging import logger


class KafkaClient:
    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: dict[str, AIOKafkaConsumer] = {}
        self._running = False

    async def connect(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            security_protocol=settings.KAFKA_SECURITY_PROTOCOL,
            sasl_mechanism=settings.KAFKA_SASL_MECHANISM,
            sasl_plain_username=settings.KAFKA_SASL_USERNAME,
            sasl_plain_password=settings.KAFKA_SASL_PASSWORD,
            enable_idempotence=settings.KAFKA_ENABLE_IDEMPOTENCE,
            max_request_size=settings.KAFKA_MAX_REQUEST_SIZE,
            compression_type="gzip",
            linger_ms=10,
            max_batch_size=65536,
            acks="all",
        )
        await self._producer.start()
        logger.info("Kafka producer connected")

    async def disconnect(self):
        if self._producer:
            await self._producer.stop()
        for consumer in self._consumers.values():
            await consumer.stop()
        logger.info("Kafka client disconnected")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def produce(self, topic: str, value: dict, key: Optional[str] = None):
        if not self._producer:
            raise RuntimeError("Kafka producer not connected")
        try:
            await self._producer.send(
                topic=topic,
                key=key.encode() if key else None,
                value=json.dumps(value).encode(),
            )
        except KafkaError as e:
            logger.error(f"Kafka produce error on {topic}: {e}", exc_info=True)
            raise

    async def consume(
        self,
        topic: str,
        group_id: str,
        handler: Callable[[dict], Awaitable[None]],
        auto_commit: bool = False,
    ):
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            security_protocol=settings.KAFKA_SECURITY_PROTOCOL,
            sasl_mechanism=settings.KAFKA_SASL_MECHANISM,
            sasl_plain_username=settings.KAFKA_SASL_USERNAME,
            sasl_plain_password=settings.KAFKA_SASL_PASSWORD,
            auto_offset_reset="earliest",
            enable_auto_commit=auto_commit,
            max_poll_records=500,
            session_timeout_ms=30000,
            heartbeat_interval_ms=3000,
            isolation_level="read_committed",
        )
        await consumer.start()
        self._consumers[topic] = consumer

        try:
            async for msg in consumer:
                data = json.loads(msg.value.decode())
                retries = 0
                max_retries = 3
                while retries <= max_retries:
                    try:
                        await handler(data)
                        if not auto_commit:
                            await consumer.commit()
                        break
                    except Exception as e:
                        retries += 1
                        if retries > max_retries:
                            logger.error(f"Error processing message from {topic}: {e}", exc_info=True)
                            await self._send_to_dlq(topic, msg, str(e))
                        else:
                            wait = 2 ** retries
                            logger.warning(f"Retry {retries}/{max_retries} for {topic} in {wait}s: {e}")
                            await asyncio.sleep(wait)
        finally:
            await consumer.stop()

    async def _send_to_dlq(self, original_topic: str, msg, error: str):
        dlq_message = {
            "original_topic": original_topic,
            "original_partition": msg.partition,
            "original_offset": msg.offset,
            "original_key": msg.key.decode() if msg.key else None,
            "original_value": msg.value.decode(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retry_count": 0,
            "failed_at": asyncio.get_event_loop().time(),
        }
        await self.produce("twin.cx.dead.letter", dlq_message)

    async def create_topic(self, topic: str, partitions: int = 6, replication: int = 3):
        try:
            existing = await self._producer.client._metadata(topic)
            if topic not in existing.topics:
                await self._producer.client._create_topic(
                    topic, partitions, replication
                )
                logger.info(f"Created topic: {topic}")
        except Exception as e:
            logger.warning(f"Could not create topic {topic}: {e}")


kafka_client = KafkaClient()
