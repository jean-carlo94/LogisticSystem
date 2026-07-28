import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import class_mapper

from app.modules.events.model import ActionType
from app.modules.events.model import Event


class AuditLogger:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def log_create(self, entity_type: str, entity_id: int, user_id: int, data: Any) -> None:
        await self._log(ActionType.CREATE, entity_type, entity_id, user_id, data)

    async def log_update(self, entity_type: str, entity_id: int, user_id: int, data: Any) -> None:
        await self._log(ActionType.UPDATE, entity_type, entity_id, user_id, data)

    async def log_status_change(
        self, entity_type: str, entity_id: int, user_id: int, old_value: Any, new_value: Any
    ) -> None:
        await self._log(ActionType.STATUS_CHANGED, entity_type, entity_id, user_id,
                        {"old": old_value, "new": new_value})

    async def log_delete(self, entity_type: str, entity_id: int, user_id: int, data: Any) -> None:
        await self._log(ActionType.DELETE, entity_type, entity_id, user_id, data)

    async def _log(self, action: ActionType, entity_type: str, entity_id: int,
                   user_id: int, data: Any) -> None:
        if hasattr(data, "model_dump"):
            dumped = data.model_dump()
            if isinstance(dumped, dict):
                dumped = {k: v for k, v in dumped.items()
                          if k not in ("hashed_password",)}
            data = dumped
        elif hasattr(data, "__table__"):
            mapper = class_mapper(type(data))
            data = {
                prop.key: getattr(data, prop.key)
                for prop in mapper.column_attrs
                if prop.key not in ("hashed_password",)
            }
        description = data if isinstance(data, str) else json.dumps(data, default=str)
        if len(description) > 65536:
            description = description[:65536] + "...[truncated]"
        await Event.create(
            self._db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            description=description,
        )
