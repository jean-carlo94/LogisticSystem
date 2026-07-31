from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.core.storage import get_image_url
from app.modules.products.model import ProductState


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Laptop"])
    description: str | None = Field(
        default=None, max_length=2000, examples=["Laptop de alto rendimiento"]
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
    category_ids: list[int] = []
    tax_ids: list[int] = []


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    state: ProductState | None = None
    barcode: str | None = Field(default=None, max_length=128)
    weight_kg: float | None = Field(default=None, ge=0)
    width_cm: float | None = Field(default=None, ge=0)
    height_cm: float | None = Field(default=None, ge=0)
    depth_cm: float | None = Field(default=None, ge=0)
    category_ids: list[int] | None = None
    tax_ids: list[int] | None = None


class CategoryInfo(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TaxInfo(BaseModel):
    id: int
    name: str
    rate: float

    model_config = {"from_attributes": True}


class ProductResponse(ProductBase):
    id: int
    image_path: str | None = None
    create_at: datetime
    update_at: datetime
    categories: list[CategoryInfo] = []
    taxes: list[TaxInfo] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def image_url(self) -> str | None:
        return get_image_url(self.image_path)


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


class ProductLocationResponse(BaseModel):
    shelf_id: int
    code: str
    aisle: str
    row: int
    level: int
    quantity: int

    model_config = {"from_attributes": True}
