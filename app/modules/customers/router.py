from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.customers.deps import get_customer_service
from app.modules.customers.schema import CustomerCreate, CustomerResponse, CustomerUpdate
from app.modules.customers.service import CustomerService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=PaginatedResponse[CustomerResponse])
async def list_customers(
    pag: dict = PaginationParams,
    email: str | None = Query(default=None, description="Email del cliente"),
    document: str | None = Query(default=None, description="Documento del cliente"),
    filters: dict = FilterParams,
    service: CustomerService = Depends(get_customer_service),
    _perm: "User" = Depends(require_permission(PermissionCode.CUSTOMERS_READ)),
):
    merged = dict(filters)
    if email is not None:
        merged["email"] = email
    if document is not None:
        merged["document"] = document
    return await service.get_all(page=pag["page"], size=pag["size"], filters=merged or None)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
    user: "User" = Depends(require_permission(PermissionCode.CUSTOMERS_MANAGE)),
):
    return await service.create(data, user.id)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service),
    _perm: "User" = Depends(require_permission(PermissionCode.CUSTOMERS_READ)),
):
    return await service.get_by_id(customer_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    service: CustomerService = Depends(get_customer_service),
    user: "User" = Depends(require_permission(PermissionCode.CUSTOMERS_MANAGE)),
):
    return await service.update(customer_id, data, user.id)
