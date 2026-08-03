from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.payments.deps import get_payment_service
from app.modules.payments.schema import PaymentCreate, PaymentResponse
from app.modules.payments.service import PaymentService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/", response_model=PaginatedResponse[PaymentResponse])
async def list_payments(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: PaymentService = Depends(get_payment_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PAYMENTS_READ)),
):
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=filters or None
    )


@router.post(
    "/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED
)
async def create_payment(
    data: PaymentCreate,
    service: PaymentService = Depends(get_payment_service),
    user: "User" = Depends(require_permission(PermissionCode.PAYMENTS_MANAGE)),
):
    return await service.create(data, user.id)


@router.get("/by-sale/{sale_id}", response_model=list[PaymentResponse])
async def get_payments_by_sale(
    sale_id: int,
    service: PaymentService = Depends(get_payment_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PAYMENTS_READ)),
):
    return await service.get_by_sale(sale_id)
