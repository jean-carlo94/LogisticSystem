from __future__ import annotations

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.modules.payments.model import PaymentStatus
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schema import PaymentCreate
from app.modules.sales.model import Sale
from app.modules.sales.repository import SaleRepository


class PaymentService:
    def __init__(
        self,
        payment_repo: PaymentRepository,
        sale_repo: SaleRepository,
        audit: AuditLogger,
    ):
        self.payment_repo = payment_repo
        self.sale_repo = sale_repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse:
        skip = (page - 1) * size
        items, total = await self.payment_repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_sale(self, sale_id: int) -> list:
        return await self.payment_repo.get_by_sale(sale_id)

    async def create(self, data: PaymentCreate, user_id: int) -> dict:
        sale = await self.sale_repo.get_by_id(data.sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        if sale.status.value == "CANCELLED":
            raise ConflictException("No se puede pagar una venta cancelada")

        if sale.payment_status == PaymentStatus.REFUNDED:
            raise ConflictException("No se puede pagar una venta reembolsada")

        paid = await self.payment_repo.get_total_by_sale(data.sale_id)
        remaining = round(sale.total - paid, 2)
        if data.amount > remaining:
            raise ValidationException(
                f"El monto del pago (${data.amount:.2f}) excede el saldo pendiente "
                f"(${remaining:.2f})"
            )

        payment = await self.payment_repo.create(
            sale_id=data.sale_id,
            method=data.method,
            amount=data.amount,
            reference=data.reference,
        )

        new_total = round(paid + data.amount, 2)
        if new_total >= sale.total:
            await self.sale_repo.update(sale, payment_status=PaymentStatus.PAID)
        elif new_total > 0:
            await self.sale_repo.update(sale, payment_status=PaymentStatus.PARTIALLY_PAID)

        await self.audit.log_create("Payment", payment.id, user_id, payment)

        return payment
