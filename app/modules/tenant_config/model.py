from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DEFAULT_MODULES = [
    "products", "shelves", "categories", "sales", "orders",
    "stations", "cash_register", "taxes", "customers", "payments",
]


class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )
    modules_enabled: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=lambda: list(DEFAULT_MODULES),
    )
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
