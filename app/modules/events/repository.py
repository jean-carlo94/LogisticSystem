from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.events.model import Event


class EventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip=0, limit=100):
        return await Event.get_all(self.db, skip=skip, limit=limit, order_by=Event.create_at.desc())

    async def find_by_entity(self, entity_type, entity_id, skip=0, limit=100):
        return await Event.find_by_entity(self.db, entity_type, entity_id, skip, limit)
