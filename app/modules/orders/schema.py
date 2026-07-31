from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.orders.model import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    shelf_id: int | None = None
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)


class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    shelf_id: int | None = None
    shelf_code: str | None = None
    quantity: int
    unit_price: float
    subtotal: float


class OrderResponse(BaseModel):
    id: int
    customer_name: str
    total: float
    status: OrderStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    items: list[OrderItemResponse] = []
    created_by: int
