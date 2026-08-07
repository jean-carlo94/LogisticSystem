from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_cash_register, require_permission
from app.modules.sales.deps import get_sale_service
from app.modules.sales.schema import SaleCreate, SaleDetailResponse, SaleResponse, SaleCancelResponse, ReceiptResponse
from app.modules.sales.service import SaleService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/", response_model=PaginatedResponse[SaleResponse])
async def list_sales(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: SaleService = Depends(get_sale_service),
    _perm: "User" = Depends(require_permission(PermissionCode.SALES_READ)),
):
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=filters or None
    )


@router.post(
    "/", response_model=SaleDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_sale(
    data: SaleCreate,
    service: SaleService = Depends(get_sale_service),
    user: "User" = Depends(require_permission(PermissionCode.SALES_CREATE)),
    cash_register_id: int | None = Depends(require_cash_register),
):
    return await service.create(data, user.id, cash_register_id)


@router.get("/{sale_id}", response_model=SaleDetailResponse)
async def get_sale_detail(
    sale_id: int,
    service: SaleService = Depends(get_sale_service),
    _perm: "User" = Depends(require_permission(PermissionCode.SALES_READ)),
):
    return await service.get_by_id(sale_id)


@router.post("/{sale_id}/cancel", response_model=SaleCancelResponse)
async def cancel_sale(
    sale_id: int,
    service: SaleService = Depends(get_sale_service),
    user: "User" = Depends(require_permission(PermissionCode.SALES_CANCEL)),
):
    return await service.cancel(sale_id, user.id)


@router.get("/{sale_id}/receipt", response_model=ReceiptResponse)
async def get_sale_receipt(
    sale_id: int,
    service: SaleService = Depends(get_sale_service),
    user: "User" = Depends(require_permission(PermissionCode.SALES_READ)),
):
    return await service.get_receipt(sale_id, user.id)
