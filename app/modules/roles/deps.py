from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.roles.repository import PermissionRepository, RoleRepository, UserRoleRepository
from app.modules.roles.service import RoleService


async def get_role_service(db: AsyncSession = Depends(get_db)) -> RoleService:
    return RoleService(RoleRepository(db), PermissionRepository(db), UserRoleRepository(db))
