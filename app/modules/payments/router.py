from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_module, require_permission
from app.modules.payments.deps import get_payment_method_service, get_payment_service
from app.modules.payments.schema import (
    PaymentCreate,
    PaymentMethodCreate,
    PaymentMethodResponse,
    PaymentMethodUpdate,
    PaymentResponse,
)
from app.modules.payments.service import PaymentMethodService, PaymentService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

# --- Payment Methods ---

pm_router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])


@pm_router.get("/", response_model=PaginatedResponse[PaymentMethodResponse])
async def list_payment_methods(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: PaymentMethodService = Depends(get_payment_method_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PAYMENT_METHODS_VIEW)),
    _module: None = Depends(require_module("payments")),
):
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=filters or None
    )


@pm_router.post(
    "/", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED
)
async def create_payment_method(
    data: PaymentMethodCreate,
    service: PaymentMethodService = Depends(get_payment_method_service),
    user: "User" = Depends(require_permission(PermissionCode.PAYMENT_METHODS_CREATE)),
    _module: None = Depends(require_module("payments")),
):
    return await service.create(data.name, user.id)


@pm_router.get("/{method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    method_id: int,
    service: PaymentMethodService = Depends(get_payment_method_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PAYMENT_METHODS_VIEW)),
    _module: None = Depends(require_module("payments")),
):
    return await service.get_by_id(method_id)


@pm_router.put("/{method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    method_id: int,
    data: PaymentMethodUpdate,
    service: PaymentMethodService = Depends(get_payment_method_service),
    user: "User" = Depends(require_permission(PermissionCode.PAYMENT_METHODS_EDIT)),
    _module: None = Depends(require_module("payments")),
):
    return await service.update(method_id, data, user.id)


@pm_router.delete("/{method_id}", response_model=PaymentMethodResponse)
async def delete_payment_method(
    method_id: int,
    service: PaymentMethodService = Depends(get_payment_method_service),
    user: "User" = Depends(require_permission(PermissionCode.PAYMENT_METHODS_DELETE)),
    _module: None = Depends(require_module("payments")),
):
    return await service.delete(method_id, user.id)


# --- Payments ---

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/", response_model=PaginatedResponse[PaymentResponse])
async def list_payments(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: PaymentService = Depends(get_payment_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PAYMENTS_VIEW)),
    _module: None = Depends(require_module("payments")),
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
    user: "User" = Depends(require_permission(PermissionCode.PAYMENTS_CREATE)),
    _module: None = Depends(require_module("payments")),
):
    return await service.create(data, user.id)


@router.get("/by-sale/{sale_id}", response_model=list[PaymentResponse])
async def get_payments_by_sale(
    sale_id: int,
    service: PaymentService = Depends(get_payment_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PAYMENTS_VIEW)),
    _module: None = Depends(require_module("payments")),
):
    return await service.get_by_sale(sale_id)
