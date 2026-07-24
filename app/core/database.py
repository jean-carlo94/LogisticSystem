from typing import Any, AsyncGenerator, Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_async_engine = None
_async_session_local = None


def _get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False,
        )
    return _async_engine


def _get_sessionmaker():
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(_get_async_engine(), expire_on_commit=False)
    return _async_session_local


class Base(DeclarativeBase):
    __created_at_attr__: str = "created_at"
    __filterable_skip__: set[str] = set()

    @classmethod
    def _is_string_column(cls, col) -> bool:
        try:
            col_type = col.property.columns[0].type
            from sqlalchemy import String, Text
            return isinstance(col_type, (String, Text))
        except Exception:
            return False

    @classmethod
    def _resolve_filter_column(cls, field: str):
        col = getattr(cls, field, None)
        if col is None:
            return None
        if isinstance(col, property):
            return getattr(cls, f"_{field}", None)
        return col

    @classmethod
    def _coerce_filter_value(cls, col, value: str):
        try:
            col_info = col.property.columns[0]
            col_type = col_info.type
        except Exception:
            return value

        from sqlalchemy import Boolean, Enum as SAEnum, Float, Integer

        if isinstance(col_type, Boolean):
            return value.lower() in ("true", "1", "yes")
        if isinstance(col_type, Integer):
            return int(value)
        if isinstance(col_type, Float):
            return float(value)
        if isinstance(col_type, SAEnum):
            try:
                return col_type.enum_class(value)
            except ValueError:
                return None

        return value

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
        filters: dict | None = None,
    ) -> tuple[Sequence[Any], int]:
        from sqlalchemy import func, select

        stmt = select(cls)
        if filters:
            skip_fields = getattr(cls, "__filterable_skip__", set())
            for field, value in filters.items():
                if field in skip_fields:
                    continue
                col = cls._resolve_filter_column(field)
                if col is None:
                    continue
                coerced = cls._coerce_filter_value(col, str(value))
                if coerced is None:
                    continue
                if cls._is_string_column(col):
                    stmt = stmt.where(col.ilike(f"%{coerced}%"))
                else:
                    stmt = stmt.where(col == coerced)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await db.scalar(count_stmt)

        paginated = stmt.offset(skip).limit(limit)
        if order_by is not None:
            paginated = paginated.order_by(order_by)
        else:
            col = getattr(cls, cls.__created_at_attr__, None)
            if col is not None:
                paginated = paginated.order_by(col.desc())
        items = (await db.scalars(paginated)).all()
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
    async with _get_sessionmaker()() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
