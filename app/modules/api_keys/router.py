from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.permissions import PermissionCode
from app.core.security import require_permission
from app.modules.api_keys.deps import get_api_key_service
from app.modules.api_keys.schema import (
    ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse, ApiKeyUpdate,
)
from app.modules.api_keys.service import ApiKeyService

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/api-keys", tags=["api_keys"])


@router.get("/", response_model=PaginatedResponse[ApiKeyResponse])
async def list_api_keys(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    name: str | None = Query(default=None, description="Nombre de la API Key"),
    service: ApiKeyService = Depends(get_api_key_service),
    _perm: "User" = Depends(require_permission(PermissionCode.API_KEYS_READ)),
):
    merged = dict(filters)
    if name is not None:
        merged["name"] = name
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=merged or None
    )


@router.post(
    "/", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    data: ApiKeyCreate,
    service: ApiKeyService = Depends(get_api_key_service),
    user: "User" = Depends(require_permission(PermissionCode.API_KEYS_MANAGE)),
):
    return await service.create(data, user.id)


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: int,
    service: ApiKeyService = Depends(get_api_key_service),
    _perm: "User" = Depends(require_permission(PermissionCode.API_KEYS_READ)),
):
    return await service.get_by_id(key_id)


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: int,
    data: ApiKeyUpdate,
    service: ApiKeyService = Depends(get_api_key_service),
    user: "User" = Depends(require_permission(PermissionCode.API_KEYS_MANAGE)),
):
    return await service.update(key_id, data, user.id)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    service: ApiKeyService = Depends(get_api_key_service),
    user: "User" = Depends(require_permission(PermissionCode.API_KEYS_MANAGE)),
):
    await service.delete(key_id, user.id)
