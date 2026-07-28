from datetime import datetime

from pydantic import BaseModel

from app.modules.events.model import ActionType


class EventResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: ActionType
    user_id: int
    description: str | None = None
    create_at: datetime

    model_config = {"from_attributes": True}
