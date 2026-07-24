from datetime import datetime
from typing import Sequence

from sqlalchemy import Enum, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base
from app.modules.events.enums import ActionType


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="action_type"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    create_at: Mapped[datetime] = mapped_column(
        "createAt", server_default=func.now(), nullable=False
    )

    @classmethod
    def find_by_entity(
        cls,
        db: Session,
        entity_type: str,
        entity_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence["Event"], int]:
        base = select(cls).where(
            cls.entity_type == entity_type, cls.entity_id == entity_id
        )
        total = db.scalar(select(func.count()).select_from(base.subquery()))
        items = db.scalars(
            base.order_by(cls.create_at.desc()).offset(skip).limit(limit)
        ).all()
        return items, total
