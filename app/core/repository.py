from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


class BaseRepository(ABC):
    model: type[Base]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip: int = 0, limit: int = 100):
        return await self.model.get_all(self.db, skip=skip, limit=limit)

    async def get_by_id(self, entity_id: int):
        return await self.model.get_id(self.db, entity_id)

    async def create(self, **kwargs):
        return await self.model.create(self.db, **kwargs)

    async def update(self, entity, **kwargs):
        return await entity.update(self.db, **kwargs)

    async def delete(self, entity):
        await entity.delete(self.db)
