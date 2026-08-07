from datetime import datetime

from pydantic import BaseModel, Field


class TenantConfigUpdate(BaseModel):
    modules_enabled: list[str] = Field(..., min_length=1)


class TenantConfigResponse(BaseModel):
    id: int
    tenant_id: int
    modules_enabled: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
