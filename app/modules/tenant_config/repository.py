from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.tenant_config.model import TenantConfig


class TenantConfigRepository(BaseRepository):
    model = TenantConfig

    async def get_by_tenant(self, tenant_id: int) -> TenantConfig | None:
        result = await self.db.scalar(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        return result
