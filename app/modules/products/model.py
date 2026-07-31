from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from app.core.database import Base


class ProductState(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    NO_STOCK = "NO_STOCK"
    DISCONTINUED = "DISCONTINUED"


class Product(Base):
    __tablename__ = "products"
    __created_at_attr__ = "create_at"
    __table_args__ = (
        UniqueConstraint("tenant_id", "barcode", name="uq_product_tenant_barcode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    _name: Mapped[str] = mapped_column("name", String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    _price: Mapped[float] = mapped_column("price", Float, nullable=False)
    _stock: Mapped[int] = mapped_column("stock", Integer, default=0, nullable=False)
    state: Mapped[ProductState] = mapped_column(
        Enum(ProductState, name="product_state"),
        default=ProductState.ACTIVE,
        nullable=False,
    )
    _barcode: Mapped[str | None] = mapped_column(
        "barcode", String(128), default=None, index=True
    )
    image_path: Mapped[str | None] = mapped_column(String(500), default=None)
    _weight_kg: Mapped[float] = mapped_column("weight_kg", Float, default=0, nullable=False)
    _width_cm: Mapped[float] = mapped_column("width_cm", Float, default=0, nullable=False)
    _height_cm: Mapped[float] = mapped_column("height_cm", Float, default=0, nullable=False)
    _depth_cm: Mapped[float] = mapped_column("depth_cm", Float, default=0, nullable=False)
    create_at: Mapped[datetime] = mapped_column(
        "createAt", server_default=func.now(), nullable=False
    )
    update_at: Mapped[datetime] = mapped_column(
        "updateAt", server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value.strip()

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float):
        self._price = round(value, 2)

    @property
    def stock(self) -> int:
        return self._stock

    @stock.setter
    def stock(self, value: int):
        self._stock = max(0, value)

    @property
    def weight_kg(self) -> float:
        return self._weight_kg

    @weight_kg.setter
    def weight_kg(self, value: float):
        self._weight_kg = max(0, value)

    @property
    def width_cm(self) -> float:
        return self._width_cm

    @width_cm.setter
    def width_cm(self, value: float):
        self._width_cm = max(0, value)

    @property
    def height_cm(self) -> float:
        return self._height_cm

    @height_cm.setter
    def height_cm(self, value: float):
        self._height_cm = max(0, value)

    @property
    def depth_cm(self) -> float:
        return self._depth_cm

    @depth_cm.setter
    def depth_cm(self, value: float):
        self._depth_cm = max(0, value)

    @property
    def barcode(self) -> str | None:
        return self._barcode

    @barcode.setter
    def barcode(self, value: str | None):
        if value is not None:
            value = value.strip()
        if not value:
            value = None
        self._barcode = value

    categories: Mapped[list["Category"]] = relationship(
        "Category", secondary="product_categories", lazy="selectin"
    )

    taxes: Mapped[list["Tax"]] = relationship(
        "Tax", secondary="product_taxes", lazy="selectin"
    )
