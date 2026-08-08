from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.tenant_config.model import DEFAULT_MODULES, TenantConfig


class TenantConfigRepository(BaseRepository):
    model = TenantConfig

    async def get_by_tenant(self, tenant_id: int) -> TenantConfig | None:
        result = await self.db.scalar(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        return result

    async def ensure_config(self, tenant_id: int) -> TenantConfig:
        existing = await self.db.scalar(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        if not existing:
            existing = TenantConfig(
                tenant_id=tenant_id,
                modules_enabled=list(DEFAULT_MODULES),
            )
            self.db.add(existing)
            await self.db.flush()
        return existing
