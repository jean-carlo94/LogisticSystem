from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.modules.products.model import Product


class ProductRepository(BaseRepository):
    model = Product

    async def find_by_barcode(self, barcode: str) -> Product | None:
        return await self.db.scalar(
            select(Product).where(Product._barcode == barcode)
        )

    async def get_product_shelves(self, product_id: int):
        from app.modules.shelves.model import Shelf, ShelfItem

        result = await self.db.scalars(
            select(Shelf)
            .join(ShelfItem, ShelfItem.shelf_id == Shelf.id)
            .where(ShelfItem.product_id == product_id)
        )
        return result.all()

    async def set_product_categories(
        self, product_id: int, category_ids: list[int]
    ) -> None:
        from app.modules.categories.model import ProductCategory

        existing = await self.db.scalars(
            select(ProductCategory).where(ProductCategory.product_id == product_id)
        )
        for pc in existing:
            await self.db.delete(pc)

        if existing:
            await self.db.flush()

        for cat_id in category_ids:
            self.db.add(ProductCategory(product_id=product_id, category_id=cat_id))

        await self.db.flush()

    async def get_by_id_with_categories(self, product_id: int) -> Product | None:
        return await self.db.scalar(
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.categories))
            .execution_options(populate_existing=True)
        )

    async def get_product_locations(self, product_id: int):
        from app.modules.shelves.model import Shelf, ShelfItem

        items = await self.db.scalars(
            select(ShelfItem).where(ShelfItem.product_id == product_id)
        )
        shelf_items = items.all()

        if not shelf_items:
            return []

        shelf_ids = [si.shelf_id for si in shelf_items]
        shelves_result = await self.db.scalars(
            select(Shelf).where(Shelf.id.in_(shelf_ids))
        )
        shelves_map = {s.id: s for s in shelves_result}

        return [
            (si, shelves_map.get(si.shelf_id))
            for si in shelf_items
            if si.quantity > 0
        ]

    async def has_sale_history(self, product_id: int) -> bool:
        from app.modules.sales.model import SaleItem

        item = await self.db.scalar(
            select(SaleItem.id).where(SaleItem.product_id == product_id).limit(1)
        )
        return item is not None
