from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.stations.model import (
    Station, StationSession, StationSessionItem, SessionStatus,
)


class StationRepository(BaseRepository):
    model = Station

    async def find_by_code(self, code: str) -> Station | None:
        result = await self.db.scalar(
            select(Station).where(Station._code == code)
        )
        return result


class StationSessionRepository(BaseRepository):
    model = StationSession

    async def get_active_by_station(self, station_id: int) -> StationSession | None:
        result = await self.db.scalar(
            select(StationSession).where(
                StationSession.station_id == station_id,
                StationSession.status == SessionStatus.OPEN,
            )
        )
        return result


class StationSessionItemRepository(BaseRepository):
    model = StationSessionItem

    async def get_items_by_session(self, session_id: int) -> list[StationSessionItem]:
        result = await self.db.scalars(
            select(StationSessionItem).where(
                StationSessionItem.session_id == session_id
            )
        )
        return list(result.all())

    async def get_item_by_id(self, item_id: int) -> StationSessionItem | None:
        result = await self.db.scalar(
            select(StationSessionItem).where(StationSessionItem.id == item_id)
        )
        return result
