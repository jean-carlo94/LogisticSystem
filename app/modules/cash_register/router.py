from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.cash_register.deps import get_cash_register_crud_service, get_cash_register_service
from app.modules.cash_register.schema import (
    CashRegisterCloseRequest, CashRegisterCreate, CashRegisterOpenRequest,
    CashRegisterResponse, CashRegisterSessionResponse, CashRegisterUpdate,
)
from app.modules.cash_register.service import CashRegisterCRUDService, CashRegisterService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/cash-register", tags=["cash_register"])
registers_router = APIRouter(prefix="/cash-registers", tags=["cash_registers"])


@router.get("/", response_model=CashRegisterSessionResponse | None)
async def get_current_register(
    service: CashRegisterService = Depends(get_cash_register_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_VIEW)),
):
    return await service.get_current(user.id)


@router.post(
    "/open", response_model=CashRegisterSessionResponse, status_code=status.HTTP_201_CREATED
)
async def open_register(
    data: CashRegisterOpenRequest,
    service: CashRegisterService = Depends(get_cash_register_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_OPEN_CLOSE)),
):
    return await service.open(data, user.id)


@router.post("/close", response_model=CashRegisterSessionResponse)
async def close_register(
    data: CashRegisterCloseRequest,
    service: CashRegisterService = Depends(get_cash_register_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_OPEN_CLOSE)),
):
    return await service.close(data, user.id)


@router.get("/history", response_model=PaginatedResponse[CashRegisterSessionResponse])
async def get_register_history(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: CashRegisterService = Depends(get_cash_register_service),
    _perm: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_VIEW)),
):
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=filters or None
    )


# ── Cash Registers CRUD ──

@registers_router.get("/", response_model=PaginatedResponse[CashRegisterResponse])
async def list_registers(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,
    service: CashRegisterCRUDService = Depends(get_cash_register_crud_service),
    _perm: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_VIEW)),
):
    return await service.get_all(page=pag["page"], size=pag["size"], filters=filters or None)


@registers_router.post(
    "/", response_model=CashRegisterResponse, status_code=status.HTTP_201_CREATED
)
async def create_register(
    data: CashRegisterCreate,
    service: CashRegisterCRUDService = Depends(get_cash_register_crud_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_MANAGE_REGISTERS)),
):
    return await service.create(data, user.id)


@registers_router.get("/{register_id}", response_model=CashRegisterResponse)
async def get_register(
    register_id: int,
    service: CashRegisterCRUDService = Depends(get_cash_register_crud_service),
    _perm: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_VIEW)),
):
    return await service.get_by_id(register_id)


@registers_router.put("/{register_id}", response_model=CashRegisterResponse)
async def update_register(
    register_id: int,
    data: CashRegisterUpdate,
    service: CashRegisterCRUDService = Depends(get_cash_register_crud_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_MANAGE_REGISTERS)),
):
    return await service.update(register_id, data, user.id)


@registers_router.delete("/{register_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_register(
    register_id: int,
    service: CashRegisterCRUDService = Depends(get_cash_register_crud_service),
    user: "User" = Depends(require_permission(PermissionCode.CASH_REGISTER_MANAGE_REGISTERS)),
):
    await service.delete(register_id, user.id)
