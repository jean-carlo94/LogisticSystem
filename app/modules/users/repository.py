from sqlalchemy import select
from app.core.repository import BaseRepository
from app.modules.users.model import User


class UserRepository(BaseRepository):
    model = User

    async def find_by_email(self, email: str):
        return await User.find_by_email(self.db, email)

    async def get_user_roles(self, user_id: int):
        from app.modules.roles.model import Role, UserRole

        result = await self.db.scalars(
            select(Role).join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return result.all()

    async def get_user_permissions(self, user_id: int, is_super_admin: bool) -> list[str]:
        from app.modules.roles.model import Permission, RolePermission, UserRole

        if is_super_admin:
            perms = await self.db.scalars(select(Permission))
            return [p.code for p in perms]

        roles = await self.get_user_roles(user_id)
        if not roles:
            return []

        perm_ids = set()
        for role in roles:
            rps = await self.db.scalars(
                select(RolePermission).where(RolePermission.role_id == role.id)
            )
            for rp in rps:
                perm_ids.add(rp.permission_id)

        if not perm_ids:
            return []

        perms = await self.db.scalars(
            select(Permission).where(Permission.id.in_(perm_ids))
        )
        return [p.code for p in perms]

    async def assign_role(self, user_id: int, role_id: int) -> None:
        from app.modules.roles.model import UserRole

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

    async def role_exists(self, role_id: int) -> bool:
        from app.modules.roles.model import Role
        return await self.db.get(Role, role_id) is not None
