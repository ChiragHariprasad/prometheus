from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from typing import List, Optional
import os


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    APP_NAME: str = "PROMETHEUS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    POSTGRES_SCHEME: str = "postgresql+asyncpg"  # TODO: Production — add connection pooling (PgBouncer)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "prometheus"
    POSTGRES_PASSWORD: str = Field(default="change-me", alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = "prometheus"
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 40
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 1800
    POSTGRES_ECHO: bool = False

    @property
    def database_url(self) -> str:
        return f"{self.POSTGRES_SCHEME}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 20
    REDIS_SENTINEL: bool = False
    REDIS_SENTINEL_MASTER: str = "mymaster"
    REDIS_SENTINEL_HOSTS: List[str] = []

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_SECURITY_PROTOCOL: str = "PLAINTEXT"
    KAFKA_SASL_MECHANISM: Optional[str] = None
    KAFKA_SASL_USERNAME: Optional[str] = None
    KAFKA_SASL_PASSWORD: Optional[str] = None
    KAFKA_SCHEMA_REGISTRY_URL: Optional[str] = None
    KAFKA_CONSUMER_GROUP_PREFIX: str = "twin-cx"
    KAFKA_ENABLE_IDEMPOTENCE: bool = True
    KAFKA_MAX_REQUEST_SIZE: int = 1048576

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_PREFER_GRPC: bool = True
    QDRANT_TIMEOUT: int = 30

    JWT_SECRET_KEY: str = Field(default="change-me-in-production", alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "prometheus"
    JWT_AUDIENCE: str = "prometheus-api"

    OAUTH2_PROVIDERS: dict = {}
    SSO_SAML_ENABLED: bool = False
    SSO_SAML_METADATA_URL: Optional[str] = None
    SSO_SAML_ENTITY_ID: Optional[str] = None
    SSO_SAML_ACS_URL: Optional[str] = None

    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "20/minute"
    RATE_LIMIT_EVENTS: str = "1000/minute"

    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: str = "us-east-1"
    S3_BUCKET_TWIN_SNAPSHOTS: str = "prometheus-twin-snapshots"
    S3_BUCKET_EVENT_ARCHIVE: str = "prometheus-event-archive"
    S3_BUCKET_MODEL_ARTIFACTS: str = "prometheus-model-artifacts"
    S3_BUCKET_EXPORTS: str = "prometheus-exports"

    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME_PREFIX: str = "twin-cx"
    MLFLOW_MODEL_REGISTRY_URI: str = "http://localhost:5000"

    EMBEDDING_MODEL_NAME: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DEVICE: str = "cuda"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_LENGTH: int = 512

    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: Optional[str] = None
    CLICKHOUSE_DATABASE: str = "prometheus_analytics"

    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    OPENTELEMETRY_ENABLED: bool = True
    OPENTELEMETRY_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OPENTELEMETRY_SERVICE_NAME: str = "prometheus-backend"

    CACHE_TTL_DEFAULT: int = 300
    CACHE_TTL_TWIN: int = 3600
    CACHE_TTL_SEGMENT: int = 1800
    CACHE_TTL_PREDICTION: int = 600
    CACHE_TTL_RECOMMENDATION: int = 300

    EVENTS_RETENTION_DAYS: int = 90
    TWIN_STALENESS_HALF_LIFE_DAYS: int = 7
    TWIN_STALENESS_THRESHOLD: float = 0.5
    TWIN_BUILD_BATCH_SIZE: int = 1000
    TWIN_UPDATE_COOLDOWN_SECONDS: int = 300

    SIMULATION_DEFAULT_ITERATIONS: int = 1000
    SIMULATION_DEFAULT_SAMPLE_SIZE: int = 10000
    SIMULATION_DEFAULT_TIME_HORIZON_DAYS: int = 30
    SIMULATION_CONFIDENCE_LEVEL: float = 0.95
    SIMULATION_PARALLEL_WORKERS: int = 4
    SIMULATION_BATCH_SIZE: int = 100

    NOTIFICATION_EMAIL_ENABLED: bool = True
    NOTIFICATION_SMS_ENABLED: bool = False
    NOTIFICATION_PUSH_ENABLED: bool = True
    NOTIFICATION_MAX_RETRIES: int = 3
    NOTIFICATION_RETRY_DELAY_SECONDS: int = 60
    NOTIFICATION_SENDGRID_API_KEY: Optional[str] = None
    NOTIFICATION_TWILIO_ACCOUNT_SID: Optional[str] = None
    NOTIFICATION_TWILIO_AUTH_TOKEN: Optional[str] = None
    NOTIFICATION_FCM_CREDENTIALS: Optional[str] = None

    SECURITY_BCRYPT_ROUNDS: int = 12
    SECURITY_MAX_LOGIN_ATTEMPTS: int = 5
    SECURITY_LOCKOUT_DURATION_MINUTES: int = 15
    SECURITY_PASSWORD_MIN_LENGTH: int = 12
    SECURITY_PASSWORD_EXPIRY_DAYS: int = 90
    SECURITY_MFA_ENABLED: bool = False
    SECURITY_ENCRYPTION_KEY: Optional[str] = None
    SECURITY_PII_FIELDS: List[str] = ["email", "phone", "first_name", "last_name", "ip_address"]

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None

    FEATURE_FLAGS: dict = {
        "real_time_twin_updates": True,
        "ml_predictions": True,
        "campaign_simulation": True,
        "vector_search": True,
        "semantic_memory": True,
        "ab_testing": True,
        "lookalike_audiences": True,
    }


settings = Settings()
