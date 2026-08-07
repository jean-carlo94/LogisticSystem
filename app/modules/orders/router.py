from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_cash_register, require_permission
from app.modules.orders.deps import get_order_service
from app.modules.orders.schema import OrderCreate, OrderDetailResponse, OrderResponse
from app.modules.orders.service import OrderService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: OrderService = Depends(get_order_service),
    _perm: "User" = Depends(require_permission(PermissionCode.ORDERS_READ)),
):
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=filters or None
    )


@router.post(
    "/", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_order(
    data: OrderCreate,
    service: OrderService = Depends(get_order_service),
    user: "User" = Depends(require_permission(PermissionCode.ORDERS_CREATE)),
    cash_register_id: int | None = Depends(require_cash_register),
):
    return await service.create(data, user.id, cash_register_id)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: int,
    service: OrderService = Depends(get_order_service),
    _perm: "User" = Depends(require_permission(PermissionCode.ORDERS_READ)),
):
    return await service.get_by_id(order_id)


@router.post("/{order_id}/prepare", response_model=OrderDetailResponse)
async def prepare_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
    user: "User" = Depends(require_permission(PermissionCode.ORDERS_MANAGE)),
):
    return await service.transition(order_id, user.id)


@router.post("/{order_id}/ready", response_model=OrderDetailResponse)
async def ready_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
    user: "User" = Depends(require_permission(PermissionCode.ORDERS_MANAGE)),
):
    return await service.transition(order_id, user.id)


@router.post("/{order_id}/deliver", response_model=OrderDetailResponse)
async def deliver_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
    user: "User" = Depends(require_permission(PermissionCode.ORDERS_MANAGE)),
    cash_register_id: int | None = Depends(require_cash_register),
):
    return await service.deliver(order_id, user.id, cash_register_id)
