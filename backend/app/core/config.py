"""Application configuration module using Pydantic Settings."""

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global system configuration loaded from environment variables."""

    # Project Information
    PROJECT_NAME: str = "Secure Remote Code Execution Lab"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server Networking
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str | AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database Configuration (PostgreSQL Async)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "lab_admin"
    POSTGRES_PASSWORD: str = "dev_secret_password"
    POSTGRES_DB: str = "remote_lab_db"
    DATABASE_URL: str = "postgresql+asyncpg://lab_admin:dev_secret_password@localhost:5432/remote_lab_db"

    # Redis Broker & Pub/Sub
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Authentication (JWT)
    SECRET_KEY: str = "super_secret_dev_key_must_be_at_least_32_bytes_long_for_hs256"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Execution Sandbox Quotas & Limits
    SANDBOX_IMAGE_PYTHON: str = "lab-sandbox-python:3.11"
    EXECUTION_TIMEOUT_SECONDS: int = 5
    SANDBOX_MEMORY_LIMIT: str = "128m"
    SANDBOX_CPU_QUOTA: int = 50000  # 50% CPU quota (50000us per 100000us period)
    SANDBOX_MAX_PIDS: int = 64
    SANDBOX_MAX_OUTPUT_BYTES: int = 1048576  # 1 MB maximum output cap

    # Rate Limiting (Token Bucket / Sliding Window)
    RATE_LIMIT_SUBMISSIONS_PER_MINUTE: int = 15
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
