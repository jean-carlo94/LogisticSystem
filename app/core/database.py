from typing import Any, Sequence

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    @classmethod
    def _new(cls, **kwargs):
        instance = cls()
        for key, value in kwargs.items():
            setattr(instance, key, value)
        return instance

    @classmethod
    def get_id(cls, db: Session, entity_id: int):
        return db.get(cls, entity_id)

    @classmethod
    def get_all(
        cls,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        order_by=None,
    ) -> tuple[Sequence[Any], int]:
        total = db.scalar(select(func.count()).select_from(cls))
        stmt = select(cls).offset(skip).limit(limit)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        items = db.scalars(stmt).all()
        return items, total

    @classmethod
    def create(cls, db: Session, **kwargs) -> "Base":
        instance = cls._new(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance

    def save(self, db: Session) -> "Base":
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    def update(self, db: Session, **kwargs) -> "Base":
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    def delete(self, db: Session) -> None:
        db.delete(self)
        db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
