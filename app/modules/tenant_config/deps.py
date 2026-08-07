from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.tenant_config.repository import TenantConfigRepository
from app.modules.tenant_config.service import TenantConfigService


async def get_tenant_config_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> TenantConfigService:
    return TenantConfigService(TenantConfigRepository(db), audit)
