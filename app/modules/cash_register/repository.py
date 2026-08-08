from sqlalchemy import select, text as sa_text

from app.core.repository import BaseRepository
from app.modules.cash_register.model import CashRegister, CashRegisterSession, CashRegisterStatus


class CashRegisterRepository(BaseRepository):
    model = CashRegisterSession

    async def get_register_by_id(self, register_id: int) -> CashRegister | None:
        return await self.db.get(CashRegister, register_id)

    async def get_current(self, tenant_id: int, user_id: int) -> CashRegisterSession | None:
        result = await self.db.scalar(
            select(CashRegisterSession).where(
                CashRegisterSession.tenant_id == tenant_id,
                CashRegisterSession.user_id == user_id,
                CashRegisterSession.status == CashRegisterStatus.OPEN,
            )
        )
        return result

    async def get_open_for_user(self, user_id: int) -> CashRegisterSession | None:
        result = await self.db.scalar(
            select(CashRegisterSession).where(
                CashRegisterSession.user_id == user_id,
                CashRegisterSession.status == CashRegisterStatus.OPEN,
            )
        )
        return result

    async def get_open_by_register(self, cash_register_id: int) -> CashRegisterSession | None:
        result = await self.db.scalar(
            select(CashRegisterSession).where(
                CashRegisterSession.cash_register_id == cash_register_id,
                CashRegisterSession.status == CashRegisterStatus.OPEN,
            )
        )
        return result

    async def get_cash_payments_since(
        self, tenant_id: int, since
    ) -> float:
        result = await self.db.scalar(
            sa_text(
                "SELECT COALESCE(SUM(p.amount), 0) FROM payments p "
                "JOIN sales s ON s.id = p.sale_id "
                "WHERE s.tenant_id = :tid "
                "AND p.method = 'CASH' "
                "AND p.created_at >= :since",
            ).bindparams(tid=tenant_id, since=since),
        )
        return float(result)


class CashRegisterCRUDRepository(BaseRepository):
    model = CashRegister
