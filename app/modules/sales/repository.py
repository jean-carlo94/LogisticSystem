from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.sales.model import Sale, SaleItem


class SaleRepository(BaseRepository):
    model = Sale


class SaleItemRepository(BaseRepository):
    model = SaleItem

    async def get_items_by_sale(self, sale_id: int) -> list[SaleItem]:
        result = await self.db.scalars(
            select(SaleItem).where(SaleItem.sale_id == sale_id)
        )
        return list(result.all())
