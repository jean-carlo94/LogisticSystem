from __future__ import annotations

from datetime import datetime

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.tenant import current_tenant_id
from app.modules.cash_register.model import CashRegisterStatus
from app.modules.cash_register.repository import CashRegisterRepository
from app.modules.cash_register.schema import (
    CashRegisterOpenRequest, CashRegisterCloseRequest,
)


class CashRegisterService:
    def __init__(self, repo: CashRegisterRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_current(self):
        tid = current_tenant_id.get()
        if not tid:
            return None
        session = await self.repo.get_current(tid)
        if not session:
            return None
        total_cash = await self.repo.get_cash_payments_since(
            tid, session.opened_at.isoformat()
        )
        expected = round(session.opening_amount + total_cash, 2)
        return {
            **session.__dict__,
            "expected_cash": expected,
        }

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def open(self, data: CashRegisterOpenRequest, user_id: int) -> dict:
        tid = current_tenant_id.get()
        if tid is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")

        existing = await self.repo.get_current(tid)
        if existing:
            raise ConflictException("Ya existe una caja abierta. Ciérrela primero.")

        session = await self.repo.create(
            tenant_id=tid,
            user_id=user_id,
            opening_amount=data.opening_amount,
        )
        await self.audit.log_create("CashRegister", session.id, user_id, session)
        return session

    async def close(
        self, data: CashRegisterCloseRequest, user_id: int
    ) -> dict:
        tid = current_tenant_id.get()
        if tid is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")

        session = await self.repo.get_current(tid)
        if not session:
            raise NotFoundException("No hay caja abierta para cerrar")

        total_cash = await self.repo.get_cash_payments_since(
            tid, session.opened_at.isoformat()
        )
        expected = round(session.opening_amount + total_cash, 2)
        discrepancy = round(data.closing_amount - expected, 2)

        await self.repo.update(
            session,
            closing_amount=data.closing_amount,
            expected_cash=expected,
            discrepancy=discrepancy,
            notes=data.notes,
            status=CashRegisterStatus.CLOSED,
            closed_at=datetime.utcnow(),
        )

        await self.audit.log_update(
            "CashRegister", session.id, user_id,
            {"status": "CLOSED", "closing_amount": data.closing_amount,
             "expected_cash": expected, "discrepancy": discrepancy},
        )

        return session
