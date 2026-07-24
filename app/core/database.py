from typing import Any, AsyncGenerator, Sequence

from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

sync_engine = create_engine(settings.DATABASE_URL, echo=False)
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    @classmethod
    def _new(cls, **kwargs):
        instance = cls()
        for key, value in kwargs.items():
            setattr(instance, key, value)
        return instance

    @classmethod
    async def get_id(cls, db: AsyncSession, entity_id: int):
        return await db.get(cls, entity_id)

    @classmethod
    async def get_all(
        cls,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        order_by=None,
    ) -> tuple[Sequence[Any], int]:
        from sqlalchemy import func, select
        total = await db.scalar(select(func.count()).select_from(cls))
        stmt = select(cls).offset(skip).limit(limit)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        items = (await db.scalars(stmt)).all()
        return items, total

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "Base":
        instance = cls._new(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def save(self, db: AsyncSession) -> "Base":
        db.add(self)
        await db.flush()
        await db.refresh(self)
        return self

    async def update(self, db: AsyncSession, **kwargs) -> "Base":
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.add(self)
        await db.flush()
        await db.refresh(self)
        return self

    async def delete(self, db: AsyncSession) -> None:
        await db.delete(self)
        await db.flush()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
