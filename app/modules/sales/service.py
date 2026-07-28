from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.modules.products.repository import ProductRepository
from app.modules.sales.model import SaleStatus
from app.modules.sales.model import Sale
from app.modules.sales.repository import SaleItemRepository, SaleRepository
from app.modules.sales.schema import (
    SaleCreate, SaleItemResponse, SaleResponse, SaleDetailResponse,
)
from app.modules.shelves.repository import ShelfItemRepository, ShelfRepository


class SaleService:
    def __init__(
        self,
        sale_repo: SaleRepository,
        sale_item_repo: SaleItemRepository,
        shelf_item_repo: ShelfItemRepository,
        shelf_repo: ShelfRepository,
        product_repo: ProductRepository,
        audit: AuditLogger,
    ):
        self.sale_repo = sale_repo
        self.sale_item_repo = sale_item_repo
        self.shelf_item_repo = shelf_item_repo
        self.shelf_repo = shelf_repo
        self.product_repo = product_repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Sale]:
        skip = (page - 1) * size
        items, total = await self.sale_repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, sale_id: int) -> SaleDetailResponse:
        return await self._build_detail(sale_id)

    async def create(self, data: SaleCreate, user_id: int) -> SaleDetailResponse:
        if not data.items:
            raise ValidationException("La venta debe tener al menos un producto")

        product_ids = [i.product_id for i in data.items]
        products = await self.shelf_item_repo.get_products_by_ids(product_ids)
        products_map = {p.id: p for p in products}

        shelf_items = await self.shelf_item_repo.get_items_by_product_ids(product_ids)
        shelf_items_map = {(si.shelf_id, si.product_id): si for si in shelf_items}

        total = 0.0
        items_deducted = []

        for item_in in data.items:
            product = products_map.get(item_in.product_id)
            if not product:
                raise NotFoundException(
                    f"Producto {item_in.product_id} no encontrado"
                )

            shelf_item = shelf_items_map.get((item_in.shelf_id, item_in.product_id))
            if not shelf_item:
                raise NotFoundException(
                    f"Producto {item_in.product_id} no asignado a la estantería "
                    f"{item_in.shelf_id}"
                )

            if shelf_item.quantity < item_in.quantity:
                raise ConflictException(
                    f"Stock insuficiente en estantería {item_in.shelf_id} para "
                    f"'{product.name}': hay {shelf_item.quantity}, "
                    f"solicitados {item_in.quantity}"
                )

            if product.stock < item_in.quantity:
                raise ConflictException(
                    f"Stock insuficiente en inventario para '{product.name}': "
                    f"hay {product.stock}, solicitados {item_in.quantity}"
                )

            subtotal = round(item_in.quantity * item_in.unit_price, 2)
            total += subtotal

            new_shelf_qty = shelf_item.quantity - item_in.quantity
            if new_shelf_qty == 0:
                await self.shelf_item_repo.delete(shelf_item)
                await self.audit.log_delete(
                    "ShelfItem", shelf_item.id, user_id, shelf_item
                )
            else:
                await self.shelf_item_repo.update(shelf_item, quantity=new_shelf_qty)
                await self.audit.log_update(
                    "ShelfItem", shelf_item.id, user_id,
                    {"quantity": new_shelf_qty},
                )

            original_stock = product.stock
            new_stock = product.stock - item_in.quantity
            await self.product_repo.update(product, stock=new_stock)
            await self.audit.log_update(
                "Product", product.id, user_id,
                {"stock": new_stock, "previous_stock": original_stock},
            )

            items_deducted.append({
                "product": product,
                "shelf_id": item_in.shelf_id,
                "quantity": item_in.quantity,
                "unit_price": item_in.unit_price,
                "subtotal": subtotal,
            })

        sale = await self.sale_repo.create(
            customer_name=data.customer_name,
            total=round(total, 2),
            status=SaleStatus.COMPLETED,
            notes=data.notes,
            created_by=user_id,
        )

        for it in items_deducted:
            item = await self.sale_item_repo.create(
                sale_id=sale.id,
                product_id=it["product"].id,
                shelf_id=it["shelf_id"],
                quantity=it["quantity"],
                unit_price=it["unit_price"],
                subtotal=it["subtotal"],
            )
            await self.audit.log_create("SaleItem", item.id, user_id, item)

        await self.audit.log_create("Sale", sale.id, user_id, sale)

        return await self._build_detail(sale.id)

    async def _build_detail(self, sale_id: int) -> SaleDetailResponse:
        sale = await self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        items = await self.sale_item_repo.get_items_by_sale(sale_id)

        product_ids = list(set(i.product_id for i in items))
        shelf_ids = list(set(i.shelf_id for i in items))

        products_map = {}
        if product_ids:
            products = await self.shelf_item_repo.get_products_by_ids(product_ids)
            products_map = {p.id: p for p in products}

        shelves_map = {}
        if shelf_ids:
            shelves = await self.shelf_repo.get_shelves_by_ids(shelf_ids)
            shelves_map = {s.id: s for s in shelves}

        item_responses = []
        for item in items:
            product = products_map.get(item.product_id)
            shelf = shelves_map.get(item.shelf_id)
            item_responses.append(
                SaleItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=product.name if product else "?",
                    shelf_id=item.shelf_id,
                    shelf_code=shelf.code if shelf else "?",
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
            )

        return SaleDetailResponse(
            id=sale.id,
            customer_name=sale.customer_name,
            total=sale.total,
            status=sale.status,
            notes=sale.notes,
            created_by=sale.created_by,
            created_at=sale.created_at,
            items=item_responses,
        )
