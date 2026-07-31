from sqlalchemy import select

from app.core.repository import BaseRepository
from app.core.tenant import current_tenant_id
from app.modules.categories.model import Category


class CategoryRepository(BaseRepository):
    model = Category

    async def find_by_name(self, name: str) -> Category | None:
        tid = current_tenant_id.get()
        stmt = select(Category).where(Category._name == name.strip())
        if tid is not None:
            stmt = stmt.where(Category.tenant_id == tid)
        return await self.db.scalar(stmt)
