from datetime import datetime

from sqlalchemy import Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.products.enums import ProductState


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    _name: Mapped[str] = mapped_column("name", String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    _price: Mapped[float] = mapped_column("price", Float, nullable=False)
    _stock: Mapped[int] = mapped_column("stock", Integer, default=0, nullable=False)
    state: Mapped[ProductState] = mapped_column(
        Enum(ProductState, name="product_state"),
        default=ProductState.ACTIVE,
        nullable=False,
    )
    create_at: Mapped[datetime] = mapped_column(
        "createAt", server_default=func.now(), nullable=False
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
