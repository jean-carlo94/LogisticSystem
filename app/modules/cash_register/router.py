from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.cash_register.deps import get_cash_register_service
from app.modules.cash_register.schema import (
    CashRegisterOpenRequest, CashRegisterCloseRequest, CashRegisterResponse,
)
from app.modules.cash_register.service import CashRegisterService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/cash-register", tags=["cash_register"])


@router.get("/", response_model=CashRegisterResponse | None)
async def get_current_register(
    service: CashRegisterService = Depends(get_cash_register_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_READ)),
):
    return await service.get_current(user.id)


@router.post(
    "/open", response_model=CashRegisterResponse, status_code=status.HTTP_201_CREATED
)
async def open_register(
    data: CashRegisterOpenRequest,
    service: CashRegisterService = Depends(get_cash_register_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_MANAGE)),
):
    return await service.open(data, user.id)


@router.post("/close", response_model=CashRegisterResponse)
async def close_register(
    data: CashRegisterCloseRequest,
    service: CashRegisterService = Depends(get_cash_register_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_MANAGE)),
):
    return await service.close(data, user.id)


@router.get("/history", response_model=PaginatedResponse[CashRegisterResponse])
async def get_register_history(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: CashRegisterService = Depends(get_cash_register_service),
    _perm: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_READ)),
):
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=filters or None
    )
