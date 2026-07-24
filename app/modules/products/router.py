from fastapi import APIRouter, Depends, Query, status

from app.core.exceptions import NotFoundException
from app.core.pagination import PaginatedResponse
from app.core.security import get_current_user
from app.modules.products.deps import get_product_service
from app.modules.products.schema import ProductCreate, ProductResponse, ProductUpdate
from app.modules.products.service import ProductService
from app.modules.users.model import User

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[ProductResponse]:
    return await service.get_all(page=page, size=size)


@router.get("/{product_id}", response_model=ProductResponse)
async def retrieve_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    _user: User = Depends(get_current_user),
) -> ProductResponse:
    product = await service.get_by_id(product_id)
    if not product:
        raise NotFoundException("Producto no encontrado")
    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    service: ProductService = Depends(get_product_service),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    return await service.create(product_in, user.id)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    service: ProductService = Depends(get_product_service),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    return await service.update(product_id, product_in, user.id)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    user: User = Depends(get_current_user),
) -> None:
    await service.delete(product_id, user.id)
