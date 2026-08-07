from datetime import datetime

from pydantic import BaseModel, Field


class CashRegisterOpenRequest(BaseModel):
    name: str = Field(default="Caja principal", min_length=1, max_length=100)
    opening_amount: float = Field(..., ge=0)


class CashRegisterCloseRequest(BaseModel):
    closing_amount: float = Field(..., ge=0)
    notes: str | None = Field(default=None, max_length=1000)


class CashRegisterResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    name: str | None = "Caja principal"
    opening_amount: float
    closing_amount: float | None = None
    expected_cash: float | None = None
    discrepancy: float | None = None
    notes: str | None = None
    status: str
    opened_at: datetime
    closed_at: datetime | None = None

    model_config = {"from_attributes": True}
