from datetime import datetime

from sqlalchemy import Boolean, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", server_default=func.now(), nullable=False
    )
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @classmethod
    async def find_by_email(cls, db: AsyncSession, email: str):
        return await db.scalar(select(cls).where(cls.email == email))
