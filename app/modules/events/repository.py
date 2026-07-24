from typing import Sequence

from app.modules.events.enums import ActionType
from app.modules.events.model import Event


class EventRepository:
    def __init__(self, db):
        self.db = db

    def create(
        self,
        entity_type: str,
        entity_id: int,
        action: ActionType,
        user_id: int,
        description: str | None = None,
    ) -> Event:
        return Event.create(
            self.db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            description=description,
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> tuple[Sequence[Event], int]:
        return Event.get_all(self.db, skip=skip, limit=limit, order_by=Event.create_at.desc())

    def get_by_entity(
        self, entity_type: str, entity_id: int, skip: int = 0, limit: int = 100
    ) -> tuple[Sequence[Event], int]:
        return Event.find_by_entity(self.db, entity_type, entity_id, skip, limit)
