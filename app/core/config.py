from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_HOURS: int
    API_V1_STR: str
    PROJECT_NAME: str
    CORS_ORIGINS: list[str]
    RATE_LIMIT_REQUESTS: int
    RATE_LIMIT_WINDOW: int
    REQUEST_BODY_MAX_SIZE_MB: int
    STORAGE_PATH: str
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int
    ACCOUNT_ACTIVATION_EXPIRE_HOURS: int
    FRONTEND_URL: str
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
