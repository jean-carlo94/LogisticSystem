from datetime import datetime

from pydantic import BaseModel, Field


class SaleItemCreate(BaseModel):
    product_id: int
    shelf_id: int | None = None
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)


class SaleCreate(BaseModel):
    customer_name: str = Field(default="Cliente mostrador", min_length=1, max_length=200)
    customer_email: str | None = Field(default=None, max_length=255)
    customer_phone: str | None = Field(default=None, max_length=30)
    customer_document: str | None = Field(default=None, max_length=30)
    customer_address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    items: list[SaleItemCreate] = Field(..., min_length=1)


class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    shelf_id: int | None = None
    shelf_code: str | None = None
    quantity: int
    unit_price: float
    subtotal: float
    tax_amount: float


class SaleResponse(BaseModel):
    id: int
    customer_name: str
    customer_email: str | None = None
    customer_phone: str | None = None
    customer_document: str | None = None
    customer_address: str | None = None
    customer_id: int | None = None
    total: float
    status: str
    payment_status: str = "PENDING"
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SaleCancelResponse(BaseModel):
    id: int
    status: str
    payment_status: str
    message: str


class ReceiptTaxLine(BaseModel):
    name: str
    rate: float
    amount: float


class ReceiptItemResponse(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float
    tax_amount: float
    taxes: list[ReceiptTaxLine] = []


class ReceiptResponse(BaseModel):
    sale_id: int
    store_name: str = ""
    store_slug: str = ""
    customer_name: str
    items: list[ReceiptItemResponse] = []
    subtotal: float = 0
    tax_total: float = 0
    total: float = 0
    payments: list[dict] = []
    status: str
    payment_status: str
    created_by: int
    created_at: str = ""


class SaleDetailResponse(SaleResponse):
    items: list[SaleItemResponse] = []
    created_by: int
