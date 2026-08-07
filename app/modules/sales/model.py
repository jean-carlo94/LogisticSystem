from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

import enum

from app.core.database import Base


class SaleStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Sale(Base):
    __tablename__ = "sales"
    __created_at_attr__ = "created_at"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255), default=None)
    customer_phone: Mapped[str | None] = mapped_column(String(30), default=None)
    customer_document: Mapped[str | None] = mapped_column(String(30), default=None)
    customer_address: Mapped[str | None] = mapped_column(String(500), default=None)
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="SET NULL"), default=None, index=True
    )
    total: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[SaleStatus] = mapped_column(
        Enum(SaleStatus, name="sale_status"), nullable=False, default=SaleStatus.COMPLETED
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    cash_register_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cash_register_sessions.id", ondelete="SET NULL"),
        default=None, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime, server_default=func.now(), nullable=False
    )
    invoice_pdf_path: Mapped[str | None] = mapped_column(String(500), default=None)


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    shelf_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shelves.id"), nullable=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
