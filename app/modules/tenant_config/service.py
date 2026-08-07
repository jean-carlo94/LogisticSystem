from app.core.audit import AuditLogger
from app.core.exceptions import NotFoundException, ValidationException
from app.modules.tenant_config.model import DEFAULT_MODULES, TenantConfig
from app.modules.tenant_config.repository import TenantConfigRepository
from app.modules.tenant_config.schema import TenantConfigUpdate, TenantConfigResponse
from app.modules.tenants.repository import TenantRepository


class TenantConfigService:
    def __init__(self, repo: TenantConfigRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_by_tenant(self, tenant_id: int) -> TenantConfigResponse:
        config = await self.repo.get_by_tenant(tenant_id)
        if not config:
            config = await self.repo.create(
                tenant_id=tenant_id,
                modules_enabled=list(DEFAULT_MODULES),
            )
        return config

    async def update(
        self, tenant_id: int, data: TenantConfigUpdate, user_id: int
    ) -> TenantConfigResponse:
        tenant_repo = TenantRepository(self.repo.db)
        tenant = await tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundException("Tenant no encontrado")

        valid = set(DEFAULT_MODULES)
        for mod in data.modules_enabled:
            if mod not in valid:
                raise ValidationException(f"Módulo no válido: {mod}")

        config = await self.repo.get_by_tenant(tenant_id)
        if not config:
            config = await self.repo.create(
                tenant_id=tenant_id,
                modules_enabled=data.modules_enabled,
            )
            await self.audit.log_create("TenantConfig", config.id, user_id, config)
        else:
            await self.repo.update(config, modules_enabled=data.modules_enabled)
            await self.audit.log_update(
                "TenantConfig", config.id, user_id,
                {"modules_enabled": data.modules_enabled},
            )

        return config

    async def ensure_config(self, tenant_id: int) -> None:
        existing = await self.repo.get_by_tenant(tenant_id)
        if not existing:
            await self.repo.create(
                tenant_id=tenant_id,
                modules_enabled=list(DEFAULT_MODULES),
            )

    @staticmethod
    async def is_module_enabled(db, tenant_id: int, module_name: str) -> bool:
        from sqlalchemy import select
        config = await db.scalar(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        if not config:
            return True
        return module_name in (config.modules_enabled or [])
