from datetime import datetime

from pydantic import BaseModel, Field


class ShelfBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    aisle: str = Field(default="", max_length=20)
    row: int = Field(default=0, ge=0)
    level: int = Field(default=0, ge=0)
    max_weight_kg: float = Field(default=0, ge=0)
    width_cm: float = Field(default=0, ge=0)
    height_cm: float = Field(default=0, ge=0)
    depth_cm: float = Field(default=0, ge=0)


class ShelfCreate(ShelfBase):
    pass


class ShelfUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    aisle: str | None = Field(default=None, max_length=20)
    row: int | None = Field(default=None, ge=0)
    level: int | None = Field(default=None, ge=0)
    max_weight_kg: float | None = Field(default=None, ge=0)
    width_cm: float | None = Field(default=None, ge=0)
    height_cm: float | None = Field(default=None, ge=0)
    depth_cm: float | None = Field(default=None, ge=0)


class ShelfResponse(ShelfBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShelfItemResponse(BaseModel):
    id: int
    shelf_id: int
    product_id: int
    product_name: str = ""
    quantity: int

    model_config = {"from_attributes": True}


class ShelfDetailResponse(ShelfResponse):
    items: list[ShelfItemResponse] = []
    current_weight_kg: float = 0
    current_volume_cm3: float = 0


class ShelfItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class ShelfItemUpdate(BaseModel):
    quantity: int = Field(..., ge=0)
