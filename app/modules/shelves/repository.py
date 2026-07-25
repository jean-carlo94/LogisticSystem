from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.shelves.model import Shelf, ShelfItem


class ShelfRepository(BaseRepository):
    model = Shelf

    async def get_by_code(self, code: str) -> Shelf | None:
        return await self.db.scalar(select(Shelf).where(Shelf.code == code))

    async def get_shelves_by_ids(self, shelf_ids: list[int]) -> list[Shelf]:
        result = await self.db.scalars(
            select(Shelf).where(Shelf.id.in_(shelf_ids))
        )
        return list(result.all())

    async def get_items(self, shelf_id: int):
        result = await self.db.scalars(
            select(ShelfItem).where(ShelfItem.shelf_id == shelf_id)
        )
        return result.all()


class ShelfItemRepository(BaseRepository):
    model = ShelfItem

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

    async def get_items_by_product_ids(self, product_ids: list[int]) -> list[ShelfItem]:
        result = await self.db.scalars(
            select(ShelfItem).where(ShelfItem.product_id.in_(product_ids))
        )
        return list(result.all())

    async def get_product_by_id(self, product_id: int):
        from app.modules.products.model import Product
        return await self.db.scalar(select(Product).where(Product.id == product_id))

    async def get_products_by_ids(self, product_ids: list[int]):
        from app.modules.products.model import Product
        result = await self.db.scalars(
            select(Product).where(Product.id.in_(product_ids))
        )
        return result.all()

    async def has_sale_items(self, shelf_id: int) -> bool:
        from app.modules.sales.model import SaleItem

        item = await self.db.scalar(
            select(SaleItem.id).where(SaleItem.shelf_id == shelf_id).limit(1)
        )
        return item is not None
