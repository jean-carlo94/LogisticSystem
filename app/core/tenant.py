from __future__ import annotations

from contextvars import ContextVar

current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)


async def resolve_tenant(user, x_tenant: str | None) -> int | None:
    if user.is_super_admin and x_tenant:
        from app.modules.tenants.repository import TenantRepository
        from app.core.database import _get_sessionmaker
        async with _get_sessionmaker()() as db:
            repo = TenantRepository(db)
            tenant = await repo.find_by_slug(x_tenant)
            if tenant is None:
                from app.core.exceptions import NotFoundException
                raise NotFoundException("Tenant no encontrado")
            if not tenant.is_active:
                from app.core.exceptions import ForbiddenException
                raise ForbiddenException("Este tenant está deshabilitado")
            current_tenant_id.set(tenant.id)
            return tenant.id
    if not user.is_super_admin and user.tenant_id is not None:
        current_tenant_id.set(user.tenant_id)
        return user.tenant_id
    return None
