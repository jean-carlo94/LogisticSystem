from datetime import datetime

from pydantic import BaseModel, Field


class TaxCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: float = Field(..., gt=0)
    description: str | None = Field(default=None, max_length=500)


class TaxUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    rate: float | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class TaxResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    rate: float
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
