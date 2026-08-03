from sqlalchemy import select, func

from app.core.repository import BaseRepository
from app.modules.payments.model import Payment


class PaymentRepository(BaseRepository):
    model = Payment

    async def get_by_sale(self, sale_id: int) -> list[Payment]:
        result = await self.db.scalars(
            select(Payment).where(Payment.sale_id == sale_id)
        )
        return list(result.all())

    async def get_total_by_sale(self, sale_id: int) -> float:
        result = await self.db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.sale_id == sale_id
            )
        )
        return float(result)
