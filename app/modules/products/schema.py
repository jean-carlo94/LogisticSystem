from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.products.enums import ProductState


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Laptop"])
    description: str | None = Field(
        default=None, examples=["Laptop de alto rendimiento"]
    )
    price: float = Field(..., gt=0, examples=[999.99])
    stock: int = Field(default=0, ge=0, examples=[10])
    state: ProductState = Field(default=ProductState.ACTIVE, examples=["ACTIVE"])
    barcode: str | None = Field(default=None, max_length=128)
    weight_kg: float = Field(default=0, ge=0)
    width_cm: float = Field(default=0, ge=0)
    height_cm: float = Field(default=0, ge=0)
    depth_cm: float = Field(default=0, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    state: ProductState | None = None
    barcode: str | None = Field(default=None, max_length=128)
    weight_kg: float | None = Field(default=None, ge=0)
    width_cm: float | None = Field(default=None, ge=0)
    height_cm: float | None = Field(default=None, ge=0)
    depth_cm: float | None = Field(default=None, ge=0)


class ProductResponse(ProductBase):
    id: int
    image_path: str | None = None
    image_url: str | None = None
    create_at: datetime
    update_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_image_url(self) -> "ProductResponse":
        if self.image_path:
            self.image_url = f"/static/{self.image_path}"
        return self


class ShelfInfo(BaseModel):
    code: str
    aisle: str
    row: int
    level: int


class ProductQRResponse(BaseModel):
    product_id: int
    name: str
    barcode: str | None = None
    shelf: ShelfInfo | None = None
