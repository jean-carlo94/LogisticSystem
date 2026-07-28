from sqlalchemy import func, select

from app.core.repository import BaseRepository
from app.modules.events.model import Event


class EventRepository(BaseRepository):
    model = Event

    async def get_all(self, skip: int = 0, limit: int = 100, filters: dict | None = None):
        return await Event.get_all(self.db, skip=skip, limit=limit, order_by=Event.create_at.desc(), filters=filters)

    async def find_by_entity(self, entity_type: str, entity_id: int, skip: int = 0, limit: int = 100):
        base = select(Event).where(
            Event.entity_type == entity_type, Event.entity_id == entity_id
        )
        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        items = (await self.db.scalars(
            base.order_by(Event.create_at.desc()).offset(skip).limit(limit)
        )).all()
        return items, total
