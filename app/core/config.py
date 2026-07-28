from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Logistic System API"
    CORS_ORIGINS: list[str] = []
    RATE_LIMIT_REQUESTS: int = 1000
    RATE_LIMIT_WINDOW: int = 60
    REQUEST_BODY_MAX_SIZE_MB: int = 10

    STORAGE_PATH: str = "static/uploads"

    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "noreply@logisticsystem.com"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    ACCOUNT_ACTIVATION_EXPIRE_HOURS: int = 24
    FRONTEND_URL: str = "http://localhost:5173"

    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long for security")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
