import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.enums import ActionType
from app.modules.events.model import Event


class AuditLogger:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def log_create(self, entity_type: str, entity_id: int, user_id: int, changes: str) -> None:
        await self._log(ActionType.CREATE, entity_type, entity_id, user_id, changes)

    async def log_update(self, entity_type: str, entity_id: int, user_id: int, changes: str) -> None:
        await self._log(ActionType.UPDATE, entity_type, entity_id, user_id, changes)

    async def log_status_change(
        self, entity_type: str, entity_id: int, user_id: int, old_value: Any, new_value: Any
    ) -> None:
        await self._log(ActionType.STATUS_CHANGED, entity_type, entity_id, user_id,
                        json.dumps({"old": old_value, "new": new_value}))

    async def log_delete(self, entity_type: str, entity_id: int, user_id: int, changes: str) -> None:
        await self._log(ActionType.DELETE, entity_type, entity_id, user_id, changes)

    async def _log(self, action: ActionType, entity_type: str, entity_id: int,
                   user_id: int, description: str) -> None:
        await Event.create(
            self._db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            description=description,
        )
