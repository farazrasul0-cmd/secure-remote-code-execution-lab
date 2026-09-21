"""Worker service configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Execution Worker configuration parameters."""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Redis Broker & Pub/Sub
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    # Database Configuration (PostgreSQL Async)
    DATABASE_URL: str = "postgresql+asyncpg://lab_admin:dev_secret_password@localhost:5432/remote_lab_db"

    # Queue Names & Channel Prefixes
    QUEUE_NAME: str = "rce:submissions"
    STREAM_CHANNEL_PREFIX: str = "rce:stream:"
    STREAM_BUFFER_PREFIX: str = "rce:buffer:"
    BUFFER_TTL_SECONDS: int = 60

    # Worker Concurrency & Prefetch
    CELERY_CONCURRENCY: int = 4
    CELERY_PREFETCH_MULTIPLIER: int = 1

    # Container Sandbox Defaults
    SANDBOX_IMAGE_PYTHON: str = "lab-sandbox-python:3.11"
    EXECUTION_TIMEOUT_SECONDS: int = 30
    SANDBOX_MEMORY_LIMIT: str = "128m"
    SANDBOX_CPU_QUOTA: int = 50000
    SANDBOX_MAX_PIDS: int = 64
    SANDBOX_MAX_OUTPUT_BYTES: int = 1048576

    # Janitor Daemon
    JANITOR_INTERVAL_SECONDS: int = 30
    CONTAINER_MAX_LEASE_SECONDS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


worker_settings = WorkerSettings()
