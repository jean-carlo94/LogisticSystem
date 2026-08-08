from __future__ import annotations

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException
from app.core.pagination import PaginatedResponse
from app.core.security import hash_password
from app.core.seed import seed_payment_methods, seed_tenant_roles
from app.modules.roles.repository import RoleRepository, UserRoleRepository
from app.modules.tenant_config.repository import TenantConfigRepository
from app.modules.users.repository import UserRepository
from app.modules.tenants.model import Tenant
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.schema import TenantCreate, TenantUpdate


class TenantService:
    def __init__(
        self,
        repo: TenantRepository,
        tenant_config_repo: TenantConfigRepository,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        user_role_repo: UserRoleRepository,
        audit: AuditLogger,
    ):
        self.repo = repo
        self.tenant_config_repo = tenant_config_repo
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.user_role_repo = user_role_repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Tenant]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def create(self, data: TenantCreate, actor_id: int) -> Tenant:
        if await self.repo.find_by_slug(data.slug):
            raise ConflictException("El slug ya está en uso")

        tenant = await self.repo.create(name=data.name, slug=data.slug, business_id=data.business_id)

        await seed_tenant_roles(tenant.id, db=self.repo.db)

        await seed_payment_methods(tenant.id, db=self.repo.db)

        await self.tenant_config_repo.ensure_config(tenant.id)

        if data.admin_email and data.admin_password:
            existing_user = await self.user_repo.find_by_email(data.admin_email)
            if existing_user:
                raise ConflictException("El email del admin ya está registrado")

            admin_user = await self.user_repo.create(
                email=data.admin_email,
                hashed_password=hash_password(data.admin_password),
                first_name="Admin",
                is_active=True,
                tenant_id=tenant.id,
            )

            admin_role = await self.role_repo.find_by_name_and_tenant("Admin", tenant.id)
            if admin_role:
                await self.user_role_repo.assign_role(admin_user.id, admin_role.id)

        await self.audit.log_create("Tenant", tenant.id, actor_id, tenant)
        return tenant

    async def get_by_id(self, tenant_id: int) -> Tenant:
        tenant = await self.repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundException("Tenant no encontrado")
        return tenant

    async def update(self, tenant_id: int, data: TenantUpdate, actor_id: int) -> Tenant:
        tenant = await self.repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundException("Tenant no encontrado")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            existing = await self.repo.find_by_name(update_data["name"])
            if existing and existing.id != tenant_id:
                raise ConflictException("El nombre ya está en uso")
        await self.repo.update(tenant, **update_data)
        await self.audit.log_update("Tenant", tenant.id, actor_id, update_data)
        return tenant

    async def delete(self, tenant_id: int, actor_id: int) -> None:
        tenant = await self.repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundException("Tenant no encontrado")
        await self.audit.log_delete("Tenant", tenant.id, actor_id, tenant)
        await self.repo.update(tenant, is_active=False)
