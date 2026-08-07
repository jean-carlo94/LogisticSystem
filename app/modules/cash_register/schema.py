from datetime import datetime

from pydantic import BaseModel, Field


class CashRegisterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CashRegisterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class CashRegisterResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CashRegisterOpenRequest(BaseModel):
    cash_register_id: int = Field(..., gt=0)
    opening_amount: float = Field(..., ge=0)


class CashRegisterCloseRequest(BaseModel):
    closing_amount: float = Field(..., ge=0)
    notes: str | None = Field(default=None, max_length=1000)


class CashRegisterSessionResponse(BaseModel):
    id: int
    tenant_id: int
    cash_register_id: int
    cash_register_name: str | None = None
    user_id: int
    opening_amount: float
    closing_amount: float | None = None
    expected_cash: float | None = None
    discrepancy: float | None = None
    notes: str | None = None
    status: str
    opened_at: datetime
    closed_at: datetime | None = None

    model_config = {"from_attributes": True}
