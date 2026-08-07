from datetime import datetime

import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.orders.model import OrderStatus


class StationStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"


class SessionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class SessionItemStatus(str, enum.Enum):
    CREATED = "CREATED"
    PREPARING = "PREPARING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_station_tenant_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    _code: Mapped[str] = mapped_column("code", String(50), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), default=None)
    area: Mapped[str | None] = mapped_column(String(50), default=None)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[StationStatus] = mapped_column(
        Enum(StationStatus, name="station_status"),
        nullable=False,
        default=StationStatus.AVAILABLE,
    )
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, value: str):
        self._code = value.strip()


class StationSession(Base):
    __tablename__ = "station_sessions"
    __created_at_attr__ = "opened_at"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="SET NULL"), default=None, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(200), default="Cliente mostrador")
    customer_email: Mapped[str | None] = mapped_column(String(255), default=None)
    customer_phone: Mapped[str | None] = mapped_column(String(30), default=None)
    customer_document: Mapped[str | None] = mapped_column(String(30), default=None)
    customer_address: Mapped[str | None] = mapped_column(String(500), default=None)
    total: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.OPEN,
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales.id", ondelete="SET NULL"), default=None, index=True
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    cash_register_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cash_register_sessions.id", ondelete="SET NULL"),
        default=None, index=True,
    )
    opened_at: Mapped[datetime] = mapped_column(
        "openedAt", DateTime, server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column("closedAt", DateTime, default=None)


class StationSessionItem(Base):
    __tablename__ = "station_session_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("station_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[SessionItemStatus] = mapped_column(
        Enum(SessionItemStatus, name="session_item_status"),
        nullable=False,
        default=SessionItemStatus.CREATED,
    )
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime, server_default=func.now(), nullable=False
    )
