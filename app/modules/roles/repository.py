from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.core.tenant import current_tenant_id
from app.modules.roles.model import Permission, Role, RolePermission, UserRole


class RoleRepository(BaseRepository):
    model = Role

    async def find_by_name(self, name: str):
        tid = current_tenant_id.get()
        stmt = select(Role).where(Role._name == name)
        if tid is not None:
            stmt = stmt.where(Role.tenant_id == tid)
        return await self.db.scalar(stmt)

    async def assign_permissions(self, role_id: int, permission_ids: list[int]) -> None:
        await self.db.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id.not_in(permission_ids),
            )
        )
        if not permission_ids:
            await self.db.flush()
            return
        existing = await self.db.scalars(
            select(RolePermission.permission_id).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id.in_(permission_ids),
            )
        )
        existing_ids = set(existing)
        for pid in permission_ids:
            if pid not in existing_ids:
                rp = RolePermission(role_id=role_id, permission_id=pid)
                self.db.add(rp)
        await self.db.flush()

    async def get_permissions(self, role_id: int):
        result = await self.db.scalars(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
        return result.all()


class PermissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self):
        result = await self.db.scalars(select(Permission).order_by(Permission.code))
        return result.all()


class UserRoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def user_exists(self, user_id: int) -> bool:
        from app.modules.users.model import User
        return await self.db.get(User, user_id) is not None

    async def get_user_tenant_id(self, user_id: int) -> int | None:
        from app.modules.users.model import User
        user = await self.db.get(User, user_id)
        if user is None:
            return None
        return user.tenant_id
