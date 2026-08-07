from datetime import datetime

from pydantic import BaseModel, Field


class PaymentMethodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class PaymentMethodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None


class PaymentMethodResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    sale_id: int
    payment_method_id: int
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
