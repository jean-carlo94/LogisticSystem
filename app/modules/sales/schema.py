from datetime import datetime

from pydantic import BaseModel, Field


class SaleItemCreate(BaseModel):
    product_id: int
    shelf_id: int
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)


class SaleCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)
    items: list[SaleItemCreate] = Field(..., min_length=1)


class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    shelf_id: int
    shelf_code: str
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class SaleResponse(BaseModel):
    id: int
    customer_name: str
    total: float
    status: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SaleDetailResponse(SaleResponse):
    items: list[SaleItemResponse] = []
    created_by: int
