from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from app.core.permissions import PermissionCode
from app.core.security import require_permission
from app.modules.tenant_config.deps import get_tenant_config_service
from app.modules.tenant_config.schema import TenantConfigResponse, TenantConfigUpdate
from app.modules.tenant_config.service import TenantConfigService

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/tenant-config", tags=["tenant_config"])


@router.get("/{tenant_id}", response_model=TenantConfigResponse)
async def get_tenant_config(
    tenant_id: int,
    service: TenantConfigService = Depends(get_tenant_config_service),
    _perm: "User" = Depends(require_permission(PermissionCode.TENANT_CONFIG_VIEW)),
):
    return await service.get_by_tenant(tenant_id)


@router.put("/{tenant_id}", response_model=TenantConfigResponse)
async def update_tenant_config(
    tenant_id: int,
    data: TenantConfigUpdate,
    service: TenantConfigService = Depends(get_tenant_config_service),
    user: "User" = Depends(require_permission(PermissionCode.TENANT_CONFIG_EDIT)),
):
    return await service.update(tenant_id, data, user.id)
