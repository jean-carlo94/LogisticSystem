from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.roles.model import Permission, Role, RolePermission, UserRole


class RoleRepository(BaseRepository):
    model = Role

    async def find_by_name(self, name: str):
        return await self.db.scalar(select(Role).where(Role.name == name))

    async def assign_permissions(self, role_id: int, permission_ids: list[int]) -> None:
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

    async def get_by_ids(self, permission_ids: list[int]):
        result = await self.db.scalars(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        return result.all()


class UserRoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_role(self, user_id: int, role_id: int) -> None:
        existing = await self.db.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
        if not existing:
            ur = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(ur)
            await self.db.flush()

    async def user_exists(self, user_id: int) -> bool:
        from app.modules.users.model import User
        return await self.db.get(User, user_id) is not None
