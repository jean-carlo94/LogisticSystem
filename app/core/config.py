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
    CORS_ORIGINS: list[str] = ["*"]
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "static/uploads"
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT: str = ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
