from sqlalchemy import select

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
