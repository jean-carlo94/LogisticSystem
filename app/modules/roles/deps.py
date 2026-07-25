from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.roles.repository import PermissionRepository, RoleRepository, UserRoleRepository
from app.modules.roles.service import RoleService


async def get_role_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> RoleService:
    return RoleService(RoleRepository(db), PermissionRepository(db), UserRoleRepository(db), audit)
