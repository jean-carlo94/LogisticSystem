from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    document: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=500)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    document: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=500)


class CustomerResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    email: str | None = None
    phone: str | None = None
    document: str | None = None
    address: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
