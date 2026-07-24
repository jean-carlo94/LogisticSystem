from app.core.audit import AuditLogger
from app.core.exceptions import NotFoundException
from app.core.pagination import PaginatedResult
from app.modules.products.enums import ProductState
from app.modules.products.model import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schema import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, repo: ProductRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(self, page: int = 1, size: int = 20) -> PaginatedResult[Product]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size)
        return PaginatedResult.of(list(items), total, page, size)

    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.repo.get_by_id(product_id)

    async def create(self, product_in: ProductCreate, user_id: int) -> Product:
        product_in.state = self._resolve_state(product_in.stock, product_in.state)
        product = await self.repo.create(**product_in.model_dump())
        await self.audit.log_create("Product", product.id, user_id, product)
        return product

    async def update(self, product_id: int, product_in: ProductUpdate, user_id: int) -> Product:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        old_state = product.state
        new_stock = product_in.stock if product_in.stock is not None else product.stock
        requested_state = product_in.state if product_in.state is not None else product.state
        resolved_state = self._resolve_state(new_stock, requested_state)

        if resolved_state != requested_state:
            product_in.state = resolved_state

        update_data = product_in.model_dump(exclude_unset=True)
        await self.repo.update(product, **update_data)

        if product.state != old_state:
            await self.audit.log_status_change(
                "Product", product.id, user_id, old_state.value, product.state.value,
            )

        await self.audit.log_update("Product", product.id, user_id, product_in)
        return product

    def _resolve_state(self, stock: int, state: ProductState) -> ProductState:
        if stock == 0:
            return ProductState.NO_STOCK
        if state == ProductState.NO_STOCK and stock > 0:
            return ProductState.ACTIVE
        return state

    async def delete(self, product_id: int, user_id: int) -> None:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        await self.audit.log_delete("Product", product.id, user_id, product)
        await self.repo.delete(product)
