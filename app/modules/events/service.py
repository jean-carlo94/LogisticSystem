from app.core.pagination import PaginatedResult
from app.modules.events.model import Event
from app.modules.events.repository import EventRepository


class EventService:
    def __init__(self, event_repo: EventRepository):
        self.event_repo = event_repo

    def get_all(self, page: int = 1, size: int = 20) -> PaginatedResult[Event]:
        skip = (page - 1) * size
        items, total = self.event_repo.get_all(skip=skip, limit=size)
        return PaginatedResult.of(list(items), total, page, size)

    def get_by_id(self, event_id: int) -> Event | None:
        return self.event_repo.get_by_id(event_id)

    def get_by_entity(
        self, entity_type: str, entity_id: int, page: int = 1, size: int = 20
    ) -> PaginatedResult[Event]:
        skip = (page - 1) * size
        items, total = self.event_repo.get_by_entity(
            entity_type, entity_id, skip=skip, limit=size
        )
        return PaginatedResult.of(list(items), total, page, size)
