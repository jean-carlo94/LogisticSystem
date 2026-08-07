from datetime import datetime

from pydantic import BaseModel, Field


class StationCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=50)
    capacity: int = Field(default=1, ge=1)


class StationUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=50)
    capacity: int | None = Field(default=None, ge=1)
    status: str | None = Field(
        default=None, pattern="^(AVAILABLE|OCCUPIED|RESERVED|MAINTENANCE)$"
    )


class StationResponse(BaseModel):
    id: int
    code: str
    name: str | None = None
    area: str | None = None
    capacity: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StationDetailResponse(StationResponse):
    active_session: "StationSessionResponse | None" = None


class SessionItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    notes: str | None = Field(default=None, max_length=500)


class SessionItemsCreate(BaseModel):
    items: list[SessionItemCreate] = Field(..., min_length=1)


class SessionItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=500)


class SessionItemResponse(BaseModel):
    id: int
    session_id: int
    product_id: int
    product_name: str = ""
    quantity: int
    unit_price: float
    subtotal: float
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}


class StationSessionResponse(BaseModel):
    id: int
    station_id: int
    customer_id: int | None = None
    customer_name: str
    total: float
    status: str
    sale_id: int | None = None
    cash_register_id: int | None = None
    created_by: int
    opened_at: datetime
    closed_at: datetime | None = None
    items: list[SessionItemResponse] = []

    model_config = {"from_attributes": True}


class SessionOpenRequest(BaseModel):
    customer_name: str = Field(default="Cliente mostrador", max_length=200)
    customer_email: str | None = Field(default=None, max_length=255)
    customer_phone: str | None = Field(default=None, max_length=30)
    customer_document: str | None = Field(default=None, max_length=30)
    customer_address: str | None = Field(default=None, max_length=500)
