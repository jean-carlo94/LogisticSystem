from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.categories.model import Category


class CategoryRepository(BaseRepository):
    model = Category

    async def find_by_name(self, name: str) -> Category | None:
        return await self.db.scalar(
            select(Category).where(Category._name == name.strip())
        )
