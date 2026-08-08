from __future__ import annotations

from datetime import datetime, timezone

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.tenant import current_tenant_id
from app.modules.cash_register.model import CashRegisterStatus
from app.modules.cash_register.repository import CashRegisterCRUDRepository, CashRegisterRepository
from app.modules.cash_register.schema import (
    CashRegisterCloseRequest, CashRegisterCreate, CashRegisterOpenRequest, CashRegisterUpdate,
)


class CashRegisterService:
    def __init__(self, repo: CashRegisterRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def _build_session_response(self, session) -> dict:
        cache = {}
        if not hasattr(self, "_register_names"):
            self._register_names = cache
        rid = session.cash_register_id
        if rid not in self._register_names:
            register = await self.repo.get_register_by_id(rid)
            self._register_names[rid] = register.name if register else None
        return {
            "id": session.id,
            "tenant_id": session.tenant_id,
            "cash_register_id": session.cash_register_id,
            "cash_register_name": None,
            "user_id": session.user_id,
            "opening_amount": session.opening_amount,
            "closing_amount": session.closing_amount,
            "expected_cash": None,
            "discrepancy": session.discrepancy,
            "notes": session.notes,
            "status": session.status.value,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
        }

    async def get_current(self, user_id: int):
        tid = current_tenant_id.get()
        if not tid:
            return None
        session = await self.repo.get_current(tid, user_id)
        if not session:
            return None
        total_cash = await self.repo.get_cash_payments_since(
            tid, session.opened_at
        )
        expected = round(session.opening_amount + total_cash, 2)
        register = await self.repo.get_register_by_id(session.cash_register_id)
        return {
            "id": session.id,
            "tenant_id": session.tenant_id,
            "cash_register_id": session.cash_register_id,
            "cash_register_name": register.name if register else None,
            "user_id": session.user_id,
            "opening_amount": session.opening_amount,
            "closing_amount": session.closing_amount,
            "expected_cash": expected,
            "discrepancy": session.discrepancy,
            "notes": session.notes,
            "status": session.status.value,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
        }

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def open(self, data: CashRegisterOpenRequest, user_id: int):
        tid = current_tenant_id.get()
        if tid is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")

        register = await self.repo.get_register_by_id(data.cash_register_id)
        if not register or register.tenant_id != tid:
            raise NotFoundException("Caja registradora no encontrada")
        if not register.is_active:
            raise ConflictException("Esta caja registradora está inactiva")

        existing_user = await self.repo.get_current(tid, user_id)
        if existing_user:
            raise ConflictException("Ya tienes una caja abierta. Ciérrala primero.")

        existing_register = await self.repo.get_open_by_register(data.cash_register_id)
        if existing_register:
            raise ConflictException("Esta caja ya está en uso por otro usuario")

        session = await self.repo.create(
            tenant_id=tid,
            user_id=user_id,
            cash_register_id=data.cash_register_id,
            opening_amount=data.opening_amount,
        )
        await self.audit.log_create("CashRegister", session.id, user_id, session)

        return {
            "id": session.id,
            "tenant_id": session.tenant_id,
            "cash_register_id": session.cash_register_id,
            "cash_register_name": register.name,
            "user_id": session.user_id,
            "opening_amount": session.opening_amount,
            "closing_amount": session.closing_amount,
            "expected_cash": None,
            "discrepancy": session.discrepancy,
            "notes": session.notes,
            "status": session.status.value,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
        }

    async def close(
        self, data: CashRegisterCloseRequest, user_id: int
    ):
        tid = current_tenant_id.get()
        if tid is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")

        session = await self.repo.get_current(tid, user_id)
        if not session:
            raise NotFoundException("No tienes una caja abierta para cerrar")

        total_cash = await self.repo.get_cash_payments_since(
            tid, session.opened_at
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
            closed_at=datetime.now(timezone.utc),
        )

        await self.audit.log_update(
            "CashRegister", session.id, user_id,
            {"status": "CLOSED", "closing_amount": data.closing_amount,
             "expected_cash": expected, "discrepancy": discrepancy},
        )

        register = await self.repo.get_register_by_id(session.cash_register_id)
        return {
            "id": session.id,
            "tenant_id": session.tenant_id,
            "cash_register_id": session.cash_register_id,
            "cash_register_name": register.name if register else None,
            "user_id": session.user_id,
            "opening_amount": session.opening_amount,
            "closing_amount": session.closing_amount,
            "expected_cash": expected,
            "discrepancy": discrepancy,
            "notes": session.notes,
            "status": session.status.value,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
        }


class CashRegisterCRUDService:
    def __init__(self, repo: CashRegisterCRUDRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(self, page=1, size=20, filters: dict | None = None):
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, register_id: int):
        register = await self.repo.get_by_id(register_id)
        if not register:
            raise NotFoundException("Caja registradora no encontrada")
        return register

    async def create(self, data: CashRegisterCreate, user_id: int):
        tid = current_tenant_id.get()
        if tid is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")
        register = await self.repo.create(name=data.name)
        await self.audit.log_create("CashRegister", register.id, user_id, register)
        return register

    async def update(self, register_id: int, data: CashRegisterUpdate, user_id: int):
        register = await self.repo.get_by_id(register_id)
        if not register:
            raise NotFoundException("Caja registradora no encontrada")
        kwargs = data.model_dump(exclude_unset=True)
        if kwargs:
            await self.repo.update(register, **kwargs)
            await self.audit.log_update("CashRegister", register.id, user_id, kwargs)
        return register

    async def delete(self, register_id: int, user_id: int):
        register = await self.repo.get_by_id(register_id)
        if not register:
            raise NotFoundException("Caja registradora no encontrada")
        await self.repo.update(register, is_active=False)
        await self.audit.log_update("CashRegister", register.id, user_id, {"is_active": False})
