from typing import Sequence

from sqlalchemy import func, select

from app.core.repository import BaseRepository
from app.modules.events.enums import ActionType
from app.modules.events.model import Event


class EventRepository(BaseRepository[Event]):
    model = Event

    def create(
        self,
        product_id: int,
        action: ActionType,
        description: str | None = None,
    ) -> Event:
        event = Event(product_id=product_id, action=action, description=description)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_all(self, skip: int = 0, limit: int = 100) -> tuple[Sequence[Event], int]:
        return super().get_all(skip, limit, order_by=Event.create_at.desc())

    def get_by_product(
        self, product_id: int, skip: int = 0, limit: int = 100
    ) -> tuple[Sequence[Event], int]:
        base = select(Event).where(Event.product_id == product_id)
        total = self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        items = self.db.scalars(
            base.order_by(Event.create_at.desc()).offset(skip).limit(limit)
        ).all()
        return items, total
