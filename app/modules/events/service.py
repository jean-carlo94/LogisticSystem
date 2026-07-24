from app.core.pagination import PaginatedResult
from app.modules.events.model import Event
from app.modules.events.repository import EventRepository


class EventService:
    def __init__(self, repo: EventRepository):
        self.repo = repo

    async def get_all(self, page: int = 1, size: int = 20, filters: dict | None = None) -> PaginatedResult[Event]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResult.of(list(items), total, page, size)

    async def get_by_id(self, event_id: int) -> Event | None:
        return await self.repo.get_by_id(event_id)

    async def get_by_entity(
        self, entity_type: str, entity_id: int, page: int = 1, size: int = 20
    ) -> PaginatedResult[Event]:
        skip = (page - 1) * size
        items, total = await self.repo.find_by_entity(entity_type, entity_id, skip, size)
        return PaginatedResult.of(list(items), total, page, size)
