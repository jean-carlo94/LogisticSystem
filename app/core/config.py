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


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
