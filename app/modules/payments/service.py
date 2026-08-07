from __future__ import annotations

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.modules.payments.model import PaymentStatus
from app.modules.payments.repository import PaymentMethodRepository, PaymentRepository
from app.modules.payments.schema import PaymentCreate
from app.modules.sales.repository import SaleRepository


class PaymentMethodService:
    def __init__(self, repo: PaymentMethodRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(self, page: int = 1, size: int = 20, filters: dict | None = None) -> PaginatedResponse:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, method_id: int):
        method = await self.repo.get_by_id(method_id)
        if not method:
            raise NotFoundException("Método de pago no encontrado")
        return method

    async def create(self, name: str, user_id: int):
        tid = self.repo._tenant_id
        existing = await self.repo.get_by_name(tid, name)
        if existing:
            raise ConflictException("Ya existe un método de pago con ese nombre")

        method = await self.repo.create(name=name, tenant_id=tid, is_active=True)
        await self.audit.log_create("PaymentMethod", method.id, user_id, method)
        return method

    async def update(self, method_id: int, data, user_id: int):
        method = await self.get_by_id(method_id)
        tid = self.repo._tenant_id

        update_kwargs = data.model_dump(exclude_unset=True)
        if "name" in update_kwargs:
            existing = await self.repo.get_by_name(tid, update_kwargs["name"])
            if existing and existing.id != method_id:
                raise ConflictException("Ya existe un método de pago con ese nombre")

        await self.repo.update(method, **update_kwargs)
        await self.audit.log_update("PaymentMethod", method.id, user_id, update_kwargs)
        return method

    async def delete(self, method_id: int, user_id: int):
        method = await self.get_by_id(method_id)

        if await self.repo.has_payments(method_id):
            raise ConflictException(
                "No se puede eliminar el método de pago porque tiene pagos asociados"
            )

        await self.audit.log_delete("PaymentMethod", method.id, user_id, method)
        await self.repo.update(method, is_active=False)
        return method


class PaymentService:
    def __init__(
        self,
        payment_repo: PaymentRepository,
        sale_repo: SaleRepository,
        payment_method_repo: PaymentMethodRepository,
        audit: AuditLogger,
    ):
        self.payment_repo = payment_repo
        self.sale_repo = sale_repo
        self.payment_method_repo = payment_method_repo
        self.audit = audit

    async def get_all(self, page: int = 1, size: int = 20, filters: dict | None = None) -> PaginatedResponse:
        skip = (page - 1) * size
        items, total = await self.payment_repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_sale(self, sale_id: int) -> list:
        return await self.payment_repo.get_by_sale(sale_id)

    async def create(self, data: PaymentCreate, user_id: int):
        sale = await self.sale_repo.get_by_id(data.sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        if sale.status.value == "CANCELLED":
            raise ConflictException("No se puede pagar una venta cancelada")

        if sale.payment_status == PaymentStatus.REFUNDED:
            raise ConflictException("No se puede pagar una venta reembolsada")

        payment_method = await self.payment_method_repo.get_by_id(data.payment_method_id)
        if not payment_method:
            raise NotFoundException("Método de pago no encontrado")

        if not payment_method.is_active:
            raise ValidationException("El método de pago no está activo")

        paid = await self.payment_repo.get_total_by_sale(data.sale_id)
        remaining = round(sale.total - paid, 2)
        if data.amount > remaining:
            raise ValidationException(
                f"El monto del pago (${data.amount:.2f}) excede el saldo pendiente "
                f"(${remaining:.2f})"
            )

        payment = await self.payment_repo.create(
            sale_id=data.sale_id,
            payment_method_id=payment_method.id,
            method=payment_method.name,
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
