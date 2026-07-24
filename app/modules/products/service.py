import json

from app.core.pagination import PaginatedResult
from app.core.audit import AuditLogger
from app.modules.products.enums import ProductState
from app.modules.products.model import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schema import ProductCreate, ProductUpdate


class ProductService:
    def __init__(
        self,
        product_repo: ProductRepository,
        audit: AuditLogger,
    ):
        self.product_repo = product_repo
        self.audit = audit

    def get_all(self, page: int = 1, size: int = 20) -> PaginatedResult[Product]:
        skip = (page - 1) * size
        items, total = self.product_repo.get_all(skip=skip, limit=size)
        return PaginatedResult.of(list(items), total, page, size)

    def get_by_id(self, product_id: int) -> Product | None:
        return self.product_repo.get_by_id(product_id)

    def create(self, product_in: ProductCreate, user_id: int) -> Product:
        product_in.state = self._resolve_state(product_in.stock, product_in.state)

        product = self.product_repo.create(product_in)
        self.audit.log_create(
            "Product", product.id, user_id,
            product_in.model_dump_json(),
        )
        return product

    def update(self, product_id: int, product_in: ProductUpdate, user_id: int) -> Product:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ValueError("Producto no encontrado")

        old_state = product.state

        new_stock = product_in.stock if product_in.stock is not None else product.stock
        requested_state = product_in.state if product_in.state is not None else product.state
        resolved_state = self._resolve_state(new_stock, requested_state)

        if resolved_state != requested_state:
            product_in.state = resolved_state

        updated = self.product_repo.update(product, product_in)

        if updated.state != old_state:
            self.audit.log_status_change(
                "Product", updated.id, user_id,
                old_state.value, updated.state.value,
            )

        self.audit.log_update(
            "Product", updated.id, user_id,
            product_in.model_dump_json(exclude_unset=True),
        )
        return updated

    def _resolve_state(
        self, stock: int, state: ProductState
    ) -> ProductState:
        if stock == 0:
            return ProductState.NO_STOCK
        if state == ProductState.NO_STOCK and stock > 0:
            return ProductState.ACTIVE
        return state

    def delete(self, product_id: int, user_id: int) -> None:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ValueError("Producto no encontrado")

        self.audit.log_delete(
            "Product", product.id, user_id,
            json.dumps({"id": product.id, "name": product.name}),
        )
        self.product_repo.delete(product)
