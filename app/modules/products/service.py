from __future__ import annotations

from fastapi import UploadFile

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.storage import generate_filename, get_storage
from app.core.tenant import current_tenant_id
from app.modules.products.model import ProductState
from app.modules.products.model import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schema import (
    ProductCreate, ProductLocationResponse, ProductQRResponse, ProductUpdate, ShelfInfo,
)


class ProductService:
    def __init__(self, repo: ProductRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Product]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.repo.get_by_id(product_id)

    async def create(self, product_in: ProductCreate, user_id: int) -> Product:
        if current_tenant_id.get() is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")
        if product_in.barcode:
            existing = await self.repo.find_by_barcode(product_in.barcode)
            if existing:
                raise ConflictException("El código de barras ya está en uso")

        category_ids = product_in.category_ids
        tax_ids = product_in.tax_ids
        data = product_in.model_dump(exclude={"category_ids", "tax_ids"})

        resolved = self._resolve_state(data["stock"], data["state"])
        data["state"] = resolved

        product = await self.repo.create(**data)

        if category_ids:
            await self.repo.set_product_categories(product.id, category_ids)
        if tax_ids:
            await self.repo.set_product_taxes(product.id, tax_ids)
        if category_ids or tax_ids:
            product = await self.repo.get_by_id_with_categories(product.id)

        await self.audit.log_create("Product", product.id, user_id, product)
        return product

    async def update(self, product_id: int, product_in: ProductUpdate, user_id: int) -> Product:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        update_data = product_in.model_dump(exclude_unset=True)
        category_ids = update_data.pop("category_ids", None)
        tax_ids = update_data.pop("tax_ids", None)

        if "barcode" in update_data and update_data["barcode"] != product.barcode:
            if update_data["barcode"]:
                existing = await self.repo.find_by_barcode(update_data["barcode"])
                if existing and existing.id != product_id:
                    raise ConflictException("El código de barras ya está en uso")

        old_state = product.state
        new_stock = update_data.get("stock", product.stock)
        requested_state = update_data.get("state", product.state)
        resolved_state = self._resolve_state(new_stock, requested_state)

        if "state" not in update_data or resolved_state != requested_state:
            update_data["state"] = resolved_state

        await self.repo.update(product, **update_data)

        if category_ids is not None:
            await self.repo.set_product_categories(product.id, category_ids)
        if tax_ids is not None:
            await self.repo.set_product_taxes(product.id, tax_ids)
        if category_ids is not None or tax_ids is not None:
            product = await self.repo.get_by_id_with_categories(product.id)

        if product.state != old_state:
            await self.audit.log_status_change(
                "Product", product.id, user_id, old_state.value, product.state.value,
            )

        await self.audit.log_update("Product", product.id, user_id, update_data)
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

        if await self.repo.has_sale_history(product_id):
            raise ConflictException(
                "No se puede eliminar un producto con historial de ventas"
            )

        if await self.repo.has_order_history(product_id):
            raise ConflictException(
                "No se puede eliminar un producto con pedidos asociados"
            )

        if product.image_path:
            storage = get_storage()
            await storage.delete(product.image_path)

        await self.audit.log_delete("Product", product.id, user_id, product)
        await self.repo.delete(product)

    async def upload_image(self, product_id: int, file: UploadFile, user_id: int) -> Product:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        storage = get_storage()
        if product.image_path:
            await storage.delete(product.image_path)

        filename = generate_filename(f"product_{product_id}", file.filename or "image.jpg")
        relative_path = f"products/{filename}"
        await storage.upload(file, relative_path)

        await self.repo.update(product, image_path=relative_path)
        await self.audit.log_update("Product", product.id, user_id, {"image_path": relative_path})
        return product

    async def delete_image(self, product_id: int, user_id: int) -> None:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        if product.image_path:
            storage = get_storage()
            await storage.delete(product.image_path)
            await self.repo.update(product, image_path=None)
            await self.audit.log_update("Product", product.id, user_id, {"image_path": None})

    async def get_qr_data(self, product_id: int) -> ProductQRResponse:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        shelf = None
        items = await self.repo.get_product_shelves(product_id)
        if items:
            first = items[0]
            shelf = ShelfInfo(
                code=first.code,
                aisle=first.aisle,
                row=first.row,
                level=first.level,
            )

        return ProductQRResponse(
            product_id=product.id,
            name=product.name,
            barcode=product.barcode,
            shelf=shelf,
        )

    async def get_locations(
        self, product_id: int
    ) -> list[ProductLocationResponse]:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        rows = await self.repo.get_product_locations(product_id)
        return [
            ProductLocationResponse(
                shelf_id=si.shelf_id,
                code=shelf.code if shelf else "?",
                aisle=shelf.aisle if shelf else "",
                row=shelf.row if shelf else 0,
                level=shelf.level if shelf else 0,
                quantity=si.quantity,
            )
            for si, shelf in rows
        ]
