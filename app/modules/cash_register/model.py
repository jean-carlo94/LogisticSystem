from datetime import datetime

import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CashRegisterStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CashRegisterSession(Base):
    __tablename__ = "cash_register_sessions"
    __created_at_attr__ = "opened_at"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(100), default="Caja principal")
    opening_amount: Mapped[float] = mapped_column(Float, nullable=False)
    closing_amount: Mapped[float | None] = mapped_column(Float, default=None)
    expected_cash: Mapped[float | None] = mapped_column(Float, default=None)
    discrepancy: Mapped[float | None] = mapped_column(Float, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[CashRegisterStatus] = mapped_column(
        Enum(CashRegisterStatus, name="cash_register_status"),
        nullable=False,
        default=CashRegisterStatus.OPEN,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
