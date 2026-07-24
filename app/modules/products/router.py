from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.exceptions import NotFoundException
from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.products.deps import get_product_service
from app.modules.products.schema import ProductCreate, ProductResponse, ProductUpdate
from app.modules.products.service import ProductService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    pag: dict = PaginationParams,
    service: ProductService = Depends(get_product_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PRODUCTS_READ)),
) -> PaginatedResponse[ProductResponse]:
    return await service.get_all(page=pag["page"], size=pag["size"])


@router.get("/{product_id}", response_model=ProductResponse)
async def retrieve_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PRODUCTS_READ)),
) -> ProductResponse:
    product = await service.get_by_id(product_id)
    if not product:
        raise NotFoundException("Producto no encontrado")
    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    service: ProductService = Depends(get_product_service),
    user: "User" = Depends(require_permission(PermissionCode.PRODUCTS_CREATE)),
) -> ProductResponse:
    return await service.create(product_in, user.id)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    service: ProductService = Depends(get_product_service),
    user: "User" = Depends(require_permission(PermissionCode.PRODUCTS_UPDATE)),
) -> ProductResponse:
    return await service.update(product_id, product_in, user.id)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    user: "User" = Depends(require_permission(PermissionCode.PRODUCTS_DELETE)),
) -> None:
    await service.delete(product_id, user.id)
