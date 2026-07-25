from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.categories.deps import get_category_service
from app.modules.categories.schema import CategoryCreate, CategoryResponse, CategoryUpdate
from app.modules.categories.service import CategoryService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    pag: dict = PaginationParams,
    name: str | None = Query(default=None, description="Nombre de la categoría"),
    filters: dict = FilterParams,
    service: CategoryService = Depends(get_category_service),
    _perm: "User" = Depends(require_permission(PermissionCode.CATEGORIES_READ)),
):
    merged = dict(filters)
    if name is not None:
        merged["name"] = name
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=merged or None
    )


@router.post(
    "/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    user: "User" = Depends(require_permission(PermissionCode.CATEGORIES_CREATE)),
):
    return await service.create(data, user.id)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
    user: "User" = Depends(require_permission(PermissionCode.CATEGORIES_UPDATE)),
):
    return await service.update(category_id, data, user.id)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
    user: "User" = Depends(require_permission(PermissionCode.CATEGORIES_DELETE)),
):
    await service.delete(category_id, user.id)
