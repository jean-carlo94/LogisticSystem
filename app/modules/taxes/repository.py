from sqlalchemy import select

from app.core.repository import BaseRepository
from app.core.tenant import current_tenant_id
from app.modules.taxes.model import Tax


class TaxRepository(BaseRepository):
    model = Tax

    async def find_by_name(self, name: str) -> Tax | None:
        tid = current_tenant_id.get()
        stmt = select(Tax).where(Tax._name == name.strip())
        if tid is not None:
            stmt = stmt.where(Tax.tenant_id == tid)
        return await self.db.scalar(stmt)
