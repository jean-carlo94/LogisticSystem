from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.tenants.model import Tenant


class TenantRepository(BaseRepository):
    model = Tenant

    async def find_by_slug(self, slug: str) -> Tenant | None:
        return await self.db.scalar(select(Tenant).where(Tenant.slug == slug))

    async def find_by_name(self, name: str) -> Tenant | None:
        return await self.db.scalar(select(Tenant).where(Tenant.name == name.strip()))
