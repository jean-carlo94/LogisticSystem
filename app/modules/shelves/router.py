from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.shelves.deps import get_shelf_service
from app.modules.shelves.schema import (
    ShelfCreate, ShelfDetailResponse, ShelfItemCreate, ShelfItemResponse,
    ShelfItemUpdate, ShelfResponse, ShelfUpdate,
)
from app.modules.shelves.service import ShelfService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/shelves", tags=["shelves"])


@router.get("/", response_model=PaginatedResponse[ShelfResponse])
async def list_shelves(
    pag: dict = PaginationParams,
    code: str | None = Query(default=None, description="Código de estantería (único)"),
    filters: dict = FilterParams,
    service: ShelfService = Depends(get_shelf_service),
    _perm: "User" = Depends(require_permission(PermissionCode.SHELVES_VIEW)),
) -> PaginatedResponse[ShelfResponse]:
    merged = dict(filters)
    if code is not None:
        merged["code"] = code
    return await service.get_all(page=pag["page"], size=pag["size"], filters=merged or None)


@router.get("/{shelf_id}", response_model=ShelfDetailResponse)
async def retrieve_shelf(
    shelf_id: int,
    service: ShelfService = Depends(get_shelf_service),
    _perm: "User" = Depends(require_permission(PermissionCode.SHELVES_VIEW)),
) -> ShelfDetailResponse:
    return await service.get_detail(shelf_id)


@router.post("/", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED)
async def create_shelf(
    data: ShelfCreate,
    service: ShelfService = Depends(get_shelf_service),
    user: "User" = Depends(require_permission(PermissionCode.SHELVES_CREATE)),
) -> ShelfResponse:
    return await service.create(data, user.id)


@router.put("/{shelf_id}", response_model=ShelfResponse)
async def update_shelf(
    shelf_id: int,
    data: ShelfUpdate,
    service: ShelfService = Depends(get_shelf_service),
    user: "User" = Depends(require_permission(PermissionCode.SHELVES_EDIT)),
) -> ShelfResponse:
    return await service.update(shelf_id, data, user.id)


@router.delete("/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shelf(
    shelf_id: int,
    service: ShelfService = Depends(get_shelf_service),
    user: "User" = Depends(require_permission(PermissionCode.SHELVES_DELETE)),
) -> None:
    await service.delete(shelf_id, user.id)


@router.post(
    "/{shelf_id}/items",
    response_model=ShelfItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item_to_shelf(
    shelf_id: int,
    data: ShelfItemCreate,
    service: ShelfService = Depends(get_shelf_service),
    user: "User" = Depends(require_permission(PermissionCode.SHELVES_ASSIGN_PRODUCTS)),
) -> ShelfItemResponse:
    return await service.add_item(shelf_id, data, user.id)


@router.put("/{shelf_id}/items/{item_id}")
async def update_item_quantity(
    shelf_id: int,
    item_id: int,
    data: ShelfItemUpdate,
    service: ShelfService = Depends(get_shelf_service),
    user: "User" = Depends(require_permission(PermissionCode.SHELVES_ASSIGN_PRODUCTS)),
):
    result = await service.update_item(shelf_id, item_id, data, user.id)
    if result is None:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
    return result


@router.delete("/{shelf_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_shelf(
    shelf_id: int,
    item_id: int,
    service: ShelfService = Depends(get_shelf_service),
    user: "User" = Depends(require_permission(PermissionCode.SHELVES_ASSIGN_PRODUCTS)),
) -> None:
    await service.remove_item(shelf_id, item_id, user.id)
