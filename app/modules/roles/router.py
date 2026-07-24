from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.pagination import PaginatedResponse
from app.core.security import get_current_user, require_permission
from app.modules.roles.deps import get_role_service
from app.modules.roles.schema import (
    AssignPermissionsRequest, AssignRoleRequest, PermissionResponse,
    RoleCreate, RoleResponse, RoleUpdate,
)
from app.modules.roles.service import RoleService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/permissions/", response_model=list[PermissionResponse])
async def list_permissions(
    service: RoleService = Depends(get_role_service),
    _perm: User = Depends(require_permission(PermissionCode.ROLES_MANAGE)),
):
    return await service.list_permissions()


@router.get("/", response_model=PaginatedResponse[RoleResponse])
async def list_roles(
    service: RoleService = Depends(get_role_service),
    _user: "User" = Depends(get_current_user),
):
    return await service.get_all()


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    service: RoleService = Depends(get_role_service),
    _perm: User = Depends(require_permission(PermissionCode.ROLES_MANAGE)),
):
    return await service.create(data)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    service: RoleService = Depends(get_role_service),
    _perm: User = Depends(require_permission(PermissionCode.ROLES_MANAGE)),
):
    return await service.update(role_id, data)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    service: RoleService = Depends(get_role_service),
    _perm: User = Depends(require_permission(PermissionCode.ROLES_MANAGE)),
):
    await service.delete(role_id)


@router.post("/{role_id}/permissions", response_model=RoleResponse)
async def assign_permissions(
    role_id: int,
    data: AssignPermissionsRequest,
    service: RoleService = Depends(get_role_service),
    _perm: User = Depends(require_permission(PermissionCode.ROLES_MANAGE)),
):
    return await service.assign_permissions(role_id, data.permission_ids)


@router.get("/{role_id}/permissions", response_model=list[PermissionResponse])
async def get_role_permissions(
    role_id: int,
    service: RoleService = Depends(get_role_service),
    _user: "User" = Depends(get_current_user),
):
    return await service.get_permissions(role_id)


@router.post("/assign", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    data: AssignRoleRequest,
    service: RoleService = Depends(get_role_service),
    _perm: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    await service.assign_role_to_user(data.user_id, data.role_id)
