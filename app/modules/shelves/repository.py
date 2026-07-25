from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.shelves.model import Shelf, ShelfItem


class ShelfRepository(BaseRepository):
    model = Shelf

    async def get_by_code(self, code: str) -> Shelf | None:
        return await self.db.scalar(select(Shelf).where(Shelf.code == code))

    async def get_items(self, shelf_id: int):
        result = await self.db.scalars(
            select(ShelfItem).where(ShelfItem.shelf_id == shelf_id)
        )
        return result.all()


class ShelfItemRepository:
    model = ShelfItem

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, item_id: int) -> ShelfItem | None:
        return await self.db.get(ShelfItem, item_id)

    async def get_by_shelf_product(self, shelf_id: int, product_id: int) -> ShelfItem | None:
        return await self.db.scalar(
            select(ShelfItem).where(
                ShelfItem.shelf_id == shelf_id,
                ShelfItem.product_id == product_id,
            )
        )

    async def get_items_by_shelf(self, shelf_id: int):
        result = await self.db.scalars(
            select(ShelfItem).where(ShelfItem.shelf_id == shelf_id)
        )
        return result.all()

    async def get_items_by_product(self, product_id: int):
        result = await self.db.scalars(
            select(ShelfItem).where(ShelfItem.product_id == product_id)
        )
        return result.all()

    async def create(self, shelf_id: int, product_id: int, quantity: int) -> ShelfItem:
        item = ShelfItem(shelf_id=shelf_id, product_id=product_id, quantity=quantity)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update(self, item: ShelfItem, quantity: int) -> ShelfItem:
        item.quantity = quantity
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete(self, item: ShelfItem) -> None:
        await self.db.delete(item)
        await self.db.flush()
