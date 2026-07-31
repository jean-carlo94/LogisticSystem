from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.tenants.deps import get_tenant_service
from app.modules.tenants.schema import TenantCreate, TenantResponse, TenantSettingsUpdate, TenantUpdate
from app.modules.tenants.service import TenantService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    pag: dict = PaginationParams,
    name: str | None = Query(default=None, description="Nombre del tenant"),
    slug: str | None = Query(default=None, description="Slug del tenant"),
    filters: dict = FilterParams,
    service: TenantService = Depends(get_tenant_service),
    _perm: "User" = Depends(require_permission(PermissionCode.TENANTS_MANAGE)),
):
    merged = dict(filters)
    if name is not None:
        merged["name"] = name
    if slug is not None:
        merged["slug"] = slug
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=merged or None
    )


@router.post(
    "/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED
)
async def create_tenant(
    data: TenantCreate,
    service: TenantService = Depends(get_tenant_service),
    user: "User" = Depends(require_permission(PermissionCode.TENANTS_MANAGE)),
):
    return await service.create(data, user.id)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    service: TenantService = Depends(get_tenant_service),
    _perm: "User" = Depends(require_permission(PermissionCode.TENANTS_MANAGE)),
):
    return await service.get_by_id(tenant_id)


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    service: TenantService = Depends(get_tenant_service),
    user: "User" = Depends(require_permission(PermissionCode.TENANTS_MANAGE)),
):
    return await service.update(tenant_id, data, user.id)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    service: TenantService = Depends(get_tenant_service),
    user: "User" = Depends(require_permission(PermissionCode.TENANTS_MANAGE)),
):
    await service.delete(tenant_id, user.id)


@router.put("/me/settings", response_model=TenantResponse)
async def update_own_tenant_settings(
    data: TenantSettingsUpdate,
    service: TenantService = Depends(get_tenant_service),
    user: "User" = Depends(require_permission(PermissionCode.ROLES_MANAGE)),
):
    from app.core.tenant import current_tenant_id
    tid = current_tenant_id.get()
    if not tid:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Solo disponible para usuarios con tenant")
    return await service.update_settings(tid, data, user.id)


@router.post("/me/api-key", response_model=TenantResponse)
async def regenerate_own_api_key(
    service: TenantService = Depends(get_tenant_service),
    user: "User" = Depends(require_permission(PermissionCode.ROLES_MANAGE)),
):
    from app.core.tenant import current_tenant_id
    tid = current_tenant_id.get()
    if not tid:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Solo disponible para usuarios con tenant")
    return await service.regenerate_api_key(tid, user.id)


@router.put("/{tenant_id}/settings", response_model=TenantResponse)
async def update_tenant_settings(
    tenant_id: int,
    data: TenantSettingsUpdate,
    service: TenantService = Depends(get_tenant_service),
    user: "User" = Depends(require_permission(PermissionCode.TENANTS_MANAGE)),
):
    return await service.update_settings(tenant_id, data, user.id)


@router.post("/{tenant_id}/api-key", response_model=TenantResponse)
async def regenerate_api_key(
    tenant_id: int,
    service: TenantService = Depends(get_tenant_service),
    user: "User" = Depends(require_permission(PermissionCode.TENANTS_MANAGE)),
):
    return await service.regenerate_api_key(tenant_id, user.id)
