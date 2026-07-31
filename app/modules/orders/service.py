from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.orders.repository import OrderItemRepository, OrderRepository
from app.modules.orders.schema import (
    OrderCreate, OrderDetailResponse, OrderItemResponse, OrderResponse,
)
from app.modules.shelves.repository import ShelfItemRepository

if TYPE_CHECKING:
    from app.modules.sales.service import SaleService


_TRANSITIONS = {
    OrderStatus.CREATED: OrderStatus.PREPARING,
    OrderStatus.PREPARING: OrderStatus.READY,
    OrderStatus.READY: OrderStatus.DELIVERED,
}


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        order_item_repo: OrderItemRepository,
        shelf_item_repo: ShelfItemRepository,
        audit: AuditLogger,
        sale_service: SaleService,
    ):
        self.order_repo = order_repo
        self.order_item_repo = order_item_repo
        self.shelf_item_repo = shelf_item_repo
        self.audit = audit
        self.sale_service = sale_service

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Order]:
        skip = (page - 1) * size
        items, total = await self.order_repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, order_id: int) -> OrderDetailResponse:
        return await self._build_detail(order_id)

    async def create(self, data: OrderCreate, user_id: int) -> OrderDetailResponse:
        if not data.items:
            raise ValidationException("El pedido debe tener al menos un producto")

        product_ids = [i.product_id for i in data.items]
        products = await self.shelf_item_repo.get_products_by_ids(product_ids)
        products_map = {p.id: p for p in products}

        shelf_ids = [i.shelf_id for i in data.items if i.shelf_id is not None]
        shelf_items_map = {}
        if shelf_ids:
            shelf_items = await self.shelf_item_repo.get_items_by_product_ids(product_ids)
            shelf_items_map = {(si.shelf_id, si.product_id): si for si in shelf_items}

        total = 0.0

        for item_in in data.items:
            product = products_map.get(item_in.product_id)
            if not product:
                raise NotFoundException(
                    f"Producto {item_in.product_id} no encontrado"
                )

            if product.stock < item_in.quantity:
                raise ConflictException(
                    f"Stock insuficiente para '{product.name}': "
                    f"hay {product.stock}, solicitados {item_in.quantity}"
                )

            if item_in.shelf_id is not None:
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

            total += round(item_in.quantity * item_in.unit_price, 2)

        order = await self.order_repo.create(
            customer_name=data.customer_name,
            total=round(total, 2),
            status=OrderStatus.CREATED,
            notes=data.notes,
            created_by=user_id,
        )

        for item_in in data.items:
            product = products_map[item_in.product_id]
            subtotal = round(item_in.quantity * item_in.unit_price, 2)
            item = await self.order_item_repo.create(
                order_id=order.id,
                product_id=item_in.product_id,
                shelf_id=item_in.shelf_id,
                quantity=item_in.quantity,
                unit_price=item_in.unit_price,
                subtotal=subtotal,
            )
            await self.audit.log_create("OrderItem", item.id, user_id, item)

        await self.audit.log_create("Order", order.id, user_id, order)

        return await self._build_detail(order.id)

    async def transition(self, order_id: int, user_id: int) -> OrderDetailResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Pedido no encontrado")

        next_status = _TRANSITIONS.get(order.status)
        if not next_status:
            raise ConflictException(
                f"El pedido en estado '{order.status.value}' no puede cambiar de estado"
            )

        previous_status = order.status
        await self.order_repo.update(order, status=next_status)
        await self.audit.log_update(
            "Order", order.id, user_id,
            {"status": next_status.value, "previous_status": previous_status.value},
        )

        return await self._build_detail(order.id)

    async def deliver(self, order_id: int, user_id: int) -> OrderDetailResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Pedido no encontrado")

        if order.status != OrderStatus.READY:
            raise ConflictException(
                f"El pedido debe estar en estado READY para ser entregado, "
                f"actual: {order.status.value}"
            )

        items = await self.order_item_repo.get_items_by_order(order.id)

        from app.modules.sales.schema import SaleCreate, SaleItemCreate

        sale_data = SaleCreate(
            customer_name=order.customer_name,
            notes=order.notes,
            items=[
                SaleItemCreate(
                    product_id=it.product_id,
                    shelf_id=it.shelf_id,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                )
                for it in items
            ],
        )

        await self.sale_service.create(sale_data, user_id)

        previous_status = order.status
        await self.order_repo.update(order, status=OrderStatus.DELIVERED)
        await self.audit.log_update(
            "Order", order.id, user_id,
            {"status": OrderStatus.DELIVERED.value, "previous_status": previous_status.value},
        )

        return await self._build_detail(order.id)

    async def _build_detail(self, order_id: int) -> OrderDetailResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Pedido no encontrado")

        items = await self.order_item_repo.get_items_by_order(order_id)

        product_ids = list(set(i.product_id for i in items))
        shelf_ids = list(set(i.shelf_id for i in items if i.shelf_id is not None))

        products_map = {}
        if product_ids:
            products = await self.shelf_item_repo.get_products_by_ids(product_ids)
            products_map = {p.id: p for p in products}

        shelves_map = {}
        if shelf_ids:
            from app.modules.shelves.repository import ShelfRepository
            shelf_repo = ShelfRepository(self.order_repo.db)
            shelves = await shelf_repo.get_shelves_by_ids(shelf_ids)
            shelves_map = {s.id: s for s in shelves}

        item_responses = []
        for item in items:
            product = products_map.get(item.product_id)
            shelf = shelves_map.get(item.shelf_id) if item.shelf_id is not None else None
            item_responses.append(
                OrderItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=product.name if product else "?",
                    shelf_id=item.shelf_id,
                    shelf_code=shelf.code if shelf else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
            )

        return OrderDetailResponse(
            id=order.id,
            customer_name=order.customer_name,
            total=order.total,
            status=order.status,
            notes=order.notes,
            created_by=order.created_by,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=item_responses,
        )
