from functools import lru_cache

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

    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "static/uploads"
    S3_BUCKET: str = ""
    S3_REGION: str = "auto"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT: str = ""
    S3_PUBLIC_URL: str = ""

    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "noreply@logisticsystem.com"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    ACCOUNT_ACTIVATION_EXPIRE_HOURS: int = 24
    FRONTEND_URL: str = "http://localhost:3000"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
