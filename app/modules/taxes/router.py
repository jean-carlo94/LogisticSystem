from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.taxes.deps import get_tax_service
from app.modules.taxes.schema import TaxCreate, TaxResponse, TaxUpdate
from app.modules.taxes.service import TaxService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/taxes", tags=["taxes"])


@router.get("/", response_model=PaginatedResponse[TaxResponse])
async def list_taxes(
    pag: dict = PaginationParams,
    name: str | None = Query(default=None, description="Nombre del impuesto"),
    filters: dict = FilterParams,
    service: TaxService = Depends(get_tax_service),
    _perm: "User" = Depends(require_permission(PermissionCode.TAXES_READ)),
):
    merged = dict(filters)
    if name is not None:
        merged["name"] = name
    return await service.get_all(page=pag["page"], size=pag["size"], filters=merged or None)


@router.post("/", response_model=TaxResponse, status_code=status.HTTP_201_CREATED)
async def create_tax(
    data: TaxCreate,
    service: TaxService = Depends(get_tax_service),
    user: "User" = Depends(require_permission(PermissionCode.TAXES_MANAGE)),
):
    return await service.create(data, user.id)


@router.put("/{tax_id}", response_model=TaxResponse)
async def update_tax(
    tax_id: int,
    data: TaxUpdate,
    service: TaxService = Depends(get_tax_service),
    user: "User" = Depends(require_permission(PermissionCode.TAXES_MANAGE)),
):
    return await service.update(tax_id, data, user.id)


@router.delete("/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax(
    tax_id: int,
    service: TaxService = Depends(get_tax_service),
    user: "User" = Depends(require_permission(PermissionCode.TAXES_MANAGE)),
):
    await service.delete(tax_id, user.id)
