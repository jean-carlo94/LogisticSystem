from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Shelf(Base):
    __tablename__ = "shelves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    aisle: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    row: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_weight_kg: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    width_cm: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    depth_cm: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ShelfItem(Base):
    __tablename__ = "shelf_items"
    __table_args__ = (
        UniqueConstraint("shelf_id", "product_id", name="uq_shelf_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shelf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shelves.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
