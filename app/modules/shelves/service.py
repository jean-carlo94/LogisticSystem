from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResult
from app.modules.products.model import Product
from app.modules.shelves.model import Shelf, ShelfItem
from app.modules.shelves.repository import ShelfItemRepository, ShelfRepository
from app.modules.shelves.schema import (
    ShelfCreate, ShelfDetailResponse, ShelfItemCreate, ShelfItemResponse,
    ShelfItemUpdate, ShelfUpdate,
)


class ShelfService:
    def __init__(
        self,
        shelf_repo: ShelfRepository,
        item_repo: ShelfItemRepository,
        audit: AuditLogger,
    ):
        self.shelf_repo = shelf_repo
        self.item_repo = item_repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResult[Shelf]:
        skip = (page - 1) * size
        items, total = await self.shelf_repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResult.of(list(items), total, page, size)

    async def get_by_id(self, shelf_id: int) -> Shelf | None:
        return await self.shelf_repo.get_by_id(shelf_id)

    async def get_detail(self, shelf_id: int) -> ShelfDetailResponse:
        shelf = await self.shelf_repo.get_by_id(shelf_id)
        if not shelf:
            raise NotFoundException("Estantería no encontrada")

        items = await self.item_repo.get_items_by_shelf(shelf_id)
        product_ids = [i.product_id for i in items]
        products_map = {}
        if product_ids:
            from sqlalchemy import select
            products = await self.shelf_repo.db.scalars(
                select(Product).where(Product.id.in_(product_ids))
            )
            products_map = {p.id: p for p in products}

        current_weight = 0.0
        current_volume = 0.0
        item_responses = []
        for item in items:
            product = products_map.get(item.product_id)
            product_name = product.name if product else "?"
            product_weight = product.weight_kg if product else 0
            product_volume = (product.width_cm * product.height_cm * product.depth_cm) if product else 0
            current_weight += product_weight * item.quantity
            current_volume += product_volume * item.quantity
            item_responses.append(
                ShelfItemResponse(
                    id=item.id,
                    shelf_id=item.shelf_id,
                    product_id=item.product_id,
                    product_name=product_name,
                    quantity=item.quantity,
                )
            )

        return ShelfDetailResponse(
            id=shelf.id,
            name=shelf.name,
            code=shelf.code,
            aisle=shelf.aisle,
            row=shelf.row,
            level=shelf.level,
            max_weight_kg=shelf.max_weight_kg,
            width_cm=shelf.width_cm,
            height_cm=shelf.height_cm,
            depth_cm=shelf.depth_cm,
            created_at=shelf.created_at,
            updated_at=shelf.updated_at,
            items=item_responses,
            current_weight_kg=round(current_weight, 2),
            current_volume_cm3=round(current_volume, 2),
        )

    async def create(self, data: ShelfCreate, user_id: int) -> Shelf:
        existing = await self.shelf_repo.get_by_code(data.code)
        if existing:
            raise ConflictException("El código de estantería ya existe")

        shelf = await self.shelf_repo.create(**data.model_dump())
        await self.audit.log_create("Shelf", shelf.id, user_id, shelf)
        return shelf

    async def update(self, shelf_id: int, data: ShelfUpdate, user_id: int) -> Shelf:
        shelf = await self.shelf_repo.get_by_id(shelf_id)
        if not shelf:
            raise NotFoundException("Estantería no encontrada")

        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data and update_data["code"] != shelf.code:
            existing = await self.shelf_repo.get_by_code(update_data["code"])
            if existing:
                raise ConflictException("El código de estantería ya existe")

        await self.shelf_repo.update(shelf, **update_data)
        await self.audit.log_update("Shelf", shelf.id, user_id, update_data)
        return shelf

    async def delete(self, shelf_id: int, user_id: int) -> None:
        shelf = await self.shelf_repo.get_by_id(shelf_id)
        if not shelf:
            raise NotFoundException("Estantería no encontrada")

        items = await self.item_repo.get_items_by_shelf(shelf_id)
        if items:
            raise ConflictException("No se puede eliminar una estantería con productos asignados")

        await self.audit.log_delete("Shelf", shelf.id, user_id, shelf)
        await self.shelf_repo.delete(shelf)

    async def add_item(self, shelf_id: int, data: ShelfItemCreate, user_id: int) -> ShelfItem:
        shelf = await self.shelf_repo.get_by_id(shelf_id)
        if not shelf:
            raise NotFoundException("Estantería no encontrada")

        product = await ShelfService._get_product(self.shelf_repo.db, data.product_id)
        if not product:
            raise NotFoundException("Producto no encontrado")

        existing = await self.item_repo.get_by_shelf_product(shelf_id, data.product_id)
        if existing:
            new_qty = existing.quantity + data.quantity
            other_weight = await self._get_total_weight(shelf_id, exclude_item_id=existing.id)
            other_volume = await self._get_total_volume(shelf_id, exclude_item_id=existing.id)
            await self._validate_capacity(shelf, product, new_qty, other_weight, other_volume)
            item = await self.item_repo.update(existing, new_qty)
            await self.audit.log_update("ShelfItem", item.id, user_id, {"quantity": new_qty})
            return item

        await self._validate_capacity(shelf, product, data.quantity)

        item = await self.item_repo.create(shelf_id, data.product_id, data.quantity)
        await self.audit.log_create("ShelfItem", item.id, user_id, item)
        return item

    async def update_item(
        self, shelf_id: int, item_id: int, data: ShelfItemUpdate, user_id: int
    ) -> ShelfItem:
        shelf = await self.shelf_repo.get_by_id(shelf_id)
        if not shelf:
            raise NotFoundException("Estantería no encontrada")

        item = await self.item_repo.get_by_id(item_id)
        if not item or item.shelf_id != shelf_id:
            raise NotFoundException("Ítem no encontrado en esta estantería")

        if data.quantity > 0:
            product = await ShelfService._get_product(self.shelf_repo.db, item.product_id)
            if not product:
                raise NotFoundException("Producto no encontrado")

            other_weight = await self._get_total_weight(shelf_id, exclude_item_id=item_id)
            other_volume = await self._get_total_volume(shelf_id, exclude_item_id=item_id)
            await self._validate_capacity(shelf, product, data.quantity, other_weight, other_volume)

        if data.quantity == 0:
            await self.item_repo.delete(item)
            await self.audit.log_delete("ShelfItem", item_id, user_id, item)
            return item

        item = await self.item_repo.update(item, data.quantity)
        await self.audit.log_update("ShelfItem", item_id, user_id, {"quantity": data.quantity})
        return item

    async def remove_item(self, shelf_id: int, item_id: int, user_id: int) -> None:
        item = await self.item_repo.get_by_id(item_id)
        if not item or item.shelf_id != shelf_id:
            raise NotFoundException("Ítem no encontrado en esta estantería")

        await self.audit.log_delete("ShelfItem", item_id, user_id, item)
        await self.item_repo.delete(item)

    async def _validate_capacity(
        self,
        shelf: Shelf,
        product,
        quantity: int,
        existing_weight: float = 0,
        existing_volume: float = 0,
    ) -> None:
        errors = []

        if shelf.width_cm > 0 and product.width_cm > shelf.width_cm:
            errors.append(
                f"Ancho del producto ({product.width_cm}cm) excede el de la estantería ({shelf.width_cm}cm)"
            )
        if shelf.height_cm > 0 and product.height_cm > shelf.height_cm:
            errors.append(
                f"Alto del producto ({product.height_cm}cm) excede el de la estantería ({shelf.height_cm}cm)"
            )
        if shelf.depth_cm > 0 and product.depth_cm > shelf.depth_cm:
            errors.append(
                f"Fondo del producto ({product.depth_cm}cm) excede el de la estantería ({shelf.depth_cm}cm)"
            )

        shelf_volume = shelf.width_cm * shelf.height_cm * shelf.depth_cm
        if shelf_volume > 0:
            product_volume = product.width_cm * product.height_cm * product.depth_cm
            added_volume = product_volume * quantity
            total_volume = existing_volume + added_volume
            if total_volume > shelf_volume:
                errors.append(
                    f"Volumen total ({total_volume:.1f}cm³) excede la capacidad ({shelf_volume:.1f}cm³)"
                )

        if shelf.max_weight_kg > 0:
            added_weight = product.weight_kg * quantity
            total = existing_weight + added_weight
            if total > shelf.max_weight_kg:
                errors.append(
                    f"Peso total ({total}kg) excede la capacidad máxima ({shelf.max_weight_kg}kg)"
                )

        if errors:
            raise ValidationException("; ".join(errors))

    async def _get_total_weight(self, shelf_id: int, exclude_item_id: int | None = None) -> float:
        items = await self.item_repo.get_items_by_shelf(shelf_id)
        total = 0.0
        for item in items:
            if exclude_item_id and item.id == exclude_item_id:
                continue
            product = await ShelfService._get_product(self.shelf_repo.db, item.product_id)
            if product:
                total += product.weight_kg * item.quantity
        return total

    async def _get_total_volume(self, shelf_id: int, exclude_item_id: int | None = None) -> float:
        items = await self.item_repo.get_items_by_shelf(shelf_id)
        total = 0.0
        for item in items:
            if exclude_item_id and item.id == exclude_item_id:
                continue
            product = await ShelfService._get_product(self.shelf_repo.db, item.product_id)
            if product:
                product_volume = product.width_cm * product.height_cm * product.depth_cm
                total += product_volume * item.quantity
        return total

    @staticmethod
    async def _get_product(db, product_id: int):
        from sqlalchemy import select
        from app.modules.products.model import Product
        return await db.scalar(select(Product).where(Product.id == product_id))
