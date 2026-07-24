from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.events.repository import EventRepository
from app.modules.events.service import EventService


async def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(EventRepository(db))
