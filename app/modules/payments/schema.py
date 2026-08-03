from datetime import datetime

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    sale_id: int
    method: str = Field(..., pattern="^(CASH|CARD|TRANSFER|WALLET|OTHER)$")
    amount: float = Field(..., gt=0)
    reference: str | None = Field(default=None, max_length=100)


class PaymentResponse(BaseModel):
    id: int
    sale_id: int
    method: str
    amount: float
    reference: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
