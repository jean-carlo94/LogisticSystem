from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    permissions: list[str] = Field(default_factory=list)
    expires_at: datetime | None = Field(default=None)


class ApiKeyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    permissions: list[str] | None = None
    is_active: bool | None = None


class ApiKeyResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    key_prefix: str
    permissions: list[str]
    is_active: bool
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str
