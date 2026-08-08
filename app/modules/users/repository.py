from datetime import datetime, timezone

from sqlalchemy import select, update

from app.core.repository import BaseRepository
from app.modules.users.model import AccountActivation, PasswordResetToken, User


class UserRepository(BaseRepository):
    model = User

    async def find_by_email(self, email: str):
        return await self.db.scalar(select(User).where(User.email == email))

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

        role_ids = [r.id for r in roles]
        perm_ids = set()
        rps = await self.db.scalars(
            select(RolePermission).where(RolePermission.role_id.in_(role_ids))
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

    async def remove_role(self, user_id: int, role_id: int) -> None:
        from app.modules.roles.model import UserRole

        ur = await self.db.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
        if ur:
            await self.db.delete(ur)
            await self.db.flush()

    async def role_exists(self, role_id: int) -> bool:
        from app.modules.roles.model import Role
        role = await self.db.get(Role, role_id)
        if role is None or self._tenant_id is None:
            return role is not None
        return role.tenant_id == self._tenant_id

    async def has_sales(self, user_id: int) -> bool:
        from app.modules.sales.model import Sale

        stmt = select(Sale.id).where(Sale.created_by == user_id).limit(1)
        if self._tenant_id is not None:
            stmt = stmt.where(Sale.tenant_id == self._tenant_id)
        s = await self.db.scalar(stmt)
        return s is not None

    async def has_orders(self, user_id: int) -> bool:
        from app.modules.orders.model import Order

        stmt = select(Order.id).where(Order.created_by == user_id).limit(1)
        if self._tenant_id is not None:
            stmt = stmt.where(Order.tenant_id == self._tenant_id)
        o = await self.db.scalar(stmt)
        return o is not None

    async def create_reset_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def invalidate_user_tokens(self, user_id: int) -> None:
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id)
            .values(used=True)
        )
        await self.db.flush()

    async def find_valid_token(self, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(timezone.utc)
        return await self.db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > now,
            )
        )

    async def create_activation_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> AccountActivation:
        token = AccountActivation(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def invalidate_user_activations(self, user_id: int) -> None:
        await self.db.execute(
            update(AccountActivation)
            .where(AccountActivation.user_id == user_id)
            .values(used=True)
        )
        await self.db.flush()

    async def find_valid_activation(self, token_hash: str) -> AccountActivation | None:
        now = datetime.now(timezone.utc)
        return await self.db.scalar(
            select(AccountActivation).where(
                AccountActivation.token_hash == token_hash,
                AccountActivation.used == False,
                AccountActivation.expires_at > now,
            )
        )
