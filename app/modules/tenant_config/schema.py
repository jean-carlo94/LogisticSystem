from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.tenant_config.model import DEFAULT_MODULES


class TenantConfigUpdate(BaseModel):
    modules_enabled: list[str] = Field(..., min_length=1)

    @classmethod
    def valid_modules(cls) -> set[str]:
        return set(DEFAULT_MODULES)


class TenantConfigResponse(BaseModel):
    id: int
    tenant_id: int
    modules_enabled: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
