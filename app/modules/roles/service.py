from __future__ import annotations

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException
from app.core.pagination import PaginatedResponse
from app.modules.roles.model import Permission, Role, UserRole
from app.modules.roles.repository import PermissionRepository, RoleRepository, UserRoleRepository
from app.modules.roles.schema import RoleCreate, RoleUpdate


class RoleService:
    def __init__(self, role_repo: RoleRepository, perm_repo: PermissionRepository,
                 user_role_repo: UserRoleRepository, audit: AuditLogger):
        self.role_repo = role_repo
        self.perm_repo = perm_repo
        self.user_role_repo = user_role_repo
        self.audit = audit

    async def get_all(self, page: int = 1, size: int = 20, filters: dict | None = None) -> PaginatedResponse[Role]:
        skip = (page - 1) * size
        items, total = await self.role_repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def create(self, data: RoleCreate) -> Role:
        if await self.role_repo.find_by_name(data.name):
            raise ConflictException("El rol ya existe")
        role = await self.role_repo.create(**data.model_dump())
        await self.audit.log_create("Role", role.id, role.id, role)
        return role

    async def update(self, role_id: int, data: RoleUpdate) -> Role:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException("Rol no encontrado")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            existing = await self.role_repo.find_by_name(update_data["name"])
            if existing and existing.id != role_id:
                raise ConflictException("El nombre ya esta en uso")
        role = await self.role_repo.update(role, **update_data)
        await self.audit.log_update("Role", role.id, role.id, update_data)
        return role

    async def delete(self, role_id: int) -> None:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException("Rol no encontrado")
        await self.audit.log_delete("Role", role.id, role.id, role)
        await self.role_repo.delete(role)

    async def assign_permissions(self, role_id: int, permission_ids: list[int]) -> Role:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException("Rol no encontrado")
        await self.role_repo.assign_permissions(role_id, permission_ids)
        return role

    async def get_permissions(self, role_id: int):
        if not await self.role_repo.get_by_id(role_id):
            raise NotFoundException("Rol no encontrado")
        return await self.role_repo.get_permissions(role_id)

    async def list_permissions(self):
        return await self.perm_repo.get_all()

    async def assign_role_to_user(self, user_id: int, role_id: int) -> None:
        if not await self.role_repo.get_by_id(role_id):
            raise NotFoundException("Rol no encontrado")
        if not await self.user_role_repo.user_exists(user_id):
            raise NotFoundException("Usuario no encontrado")
        from sqlalchemy import select
        existing = await self.user_role_repo.db.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
        if not existing:
            ur = UserRole(user_id=user_id, role_id=role_id)
            self.user_role_repo.db.add(ur)
            await self.user_role_repo.db.flush()
