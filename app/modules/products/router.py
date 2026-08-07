from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.exceptions import NotFoundException
from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.products.deps import get_product_service
from app.modules.products.schema import (
    ProductCreate, ProductLocationResponse, ProductQRResponse,
    ProductResponse, ProductUpdate,
)
from app.modules.products.service import ProductService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    pag: dict = PaginationParams,
    barcode: str | None = Query(default=None, description="Código de barras (único)"),
    filters: dict = FilterParams,
    service: ProductService = Depends(get_product_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PRODUCTS_VIEW)),
) -> PaginatedResponse[ProductResponse]:
    merged = dict(filters)
    if barcode is not None:
        merged["barcode"] = barcode
    return await service.get_all(page=pag["page"], size=pag["size"], filters=merged or None)


@router.get("/by-barcode/{barcode}", response_model=ProductResponse)
async def get_product_by_barcode(
    barcode: str,
    service: ProductService = Depends(get_product_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PRODUCTS_VIEW)),
) -> ProductResponse:
    product = await service.get_by_barcode(barcode)
    if not product:
        raise NotFoundException("Producto no encontrado")
    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def retrieve_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PRODUCTS_VIEW)),
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
    user: "User" = Depends(require_permission(PermissionCode.PRODUCTS_EDIT)),
) -> ProductResponse:
    return await service.update(product_id, product_in, user.id)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    user: "User" = Depends(require_permission(PermissionCode.PRODUCTS_DELETE)),
) -> None:
    await service.delete(product_id, user.id)


@router.post("/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    service: ProductService = Depends(get_product_service),
    user: "User" = Depends(require_permission(PermissionCode.PRODUCTS_UPLOAD_IMAGE)),
) -> ProductResponse:
    return await service.upload_image(product_id, file, user.id)


@router.delete("/{product_id}/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    user: "User" = Depends(require_permission(PermissionCode.PRODUCTS_UPLOAD_IMAGE)),
) -> None:
    await service.delete_image(product_id, user.id)


@router.get("/{product_id}/qr", response_model=ProductQRResponse)
async def get_product_qr(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PRODUCTS_VIEW)),
) -> ProductQRResponse:
    return await service.get_qr_data(product_id)


@router.get(
    "/{product_id}/locations",
    response_model=list[ProductLocationResponse],
)
async def get_product_locations(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    _perm: "User" = Depends(require_permission(PermissionCode.PRODUCTS_VIEW)),
) -> list[ProductLocationResponse]:
    return await service.get_locations(product_id)
