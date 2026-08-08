from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.roles.repository import RoleRepository, UserRoleRepository
from app.modules.tenant_config.repository import TenantConfigRepository
from app.modules.users.repository import UserRepository
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.service import TenantService


async def get_tenant_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> TenantService:
    return TenantService(
        TenantRepository(db),
        TenantConfigRepository(db),
        UserRepository(db),
        RoleRepository(db),
        UserRoleRepository(db),
        audit,
    )
