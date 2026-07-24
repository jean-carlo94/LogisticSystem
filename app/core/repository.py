from abc import ABC
from typing import Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    model: type[T]

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100, order_by=None) -> tuple[Sequence[T], int]:
        total = self.db.scalar(select(func.count()).select_from(self.model))
        stmt = select(self.model).offset(skip).limit(limit)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        items = self.db.scalars(stmt).all()
        return items, total

    def get_by_id(self, entity_id: int) -> T | None:
        return self.db.get(self.model, entity_id)
