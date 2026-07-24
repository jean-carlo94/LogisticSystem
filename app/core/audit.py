import json

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.events.enums import ActionType
from app.modules.events.repository import EventRepository


class AuditLogger:
    def __init__(self, event_repo: EventRepository):
        self._repo = event_repo

    def log_create(
        self, entity_type: str, entity_id: int, user_id: int, changes: str
    ) -> None:
        self._repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=ActionType.CREATE,
            user_id=user_id,
            description=changes,
        )

    def log_update(
        self, entity_type: str, entity_id: int, user_id: int, changes: str
    ) -> None:
        self._repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=ActionType.UPDATE,
            user_id=user_id,
            description=changes,
        )

    def log_status_change(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int,
        old_value: str,
        new_value: str,
    ) -> None:
        self._repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=ActionType.STATUS_CHANGED,
            user_id=user_id,
            description=json.dumps({"old": old_value, "new": new_value}),
        )

    def log_delete(
        self, entity_type: str, entity_id: int, user_id: int, changes: str
    ) -> None:
        self._repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=ActionType.DELETE,
            user_id=user_id,
            description=changes,
        )


def get_audit_logger(db: Session = Depends(get_db)) -> AuditLogger:
    return AuditLogger(EventRepository(db))
