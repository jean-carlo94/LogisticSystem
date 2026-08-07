from sqlalchemy import select, func

from app.core.repository import BaseRepository
from app.modules.payments.model import Payment, PaymentMethod


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


class PaymentMethodRepository(BaseRepository):
    model = PaymentMethod

    async def get_by_name(self, tenant_id: int, name: str) -> PaymentMethod | None:
        result = await self.db.scalar(
            select(PaymentMethod).where(
                PaymentMethod.tenant_id == tenant_id,
                PaymentMethod._name == name.strip(),
            )
        )
        return result

    async def has_payments(self, method_id: int) -> bool:
        result = await self.db.scalar(
            select(func.count(Payment.id)).where(
                Payment.payment_method_id == method_id,
            )
        )
        return result is not None and result > 0
