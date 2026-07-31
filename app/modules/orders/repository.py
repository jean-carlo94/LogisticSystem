from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.orders.model import Order, OrderItem


class OrderRepository(BaseRepository):
    model = Order


class OrderItemRepository(BaseRepository):
    model = OrderItem

    async def get_items_by_order(self, order_id: int) -> list[OrderItem]:
        result = await self.db.scalars(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        return list(result.all())
