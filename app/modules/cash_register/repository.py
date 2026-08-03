from sqlalchemy import text as sa_text

from app.core.repository import BaseRepository
from app.modules.cash_register.model import CashRegisterSession, CashRegisterStatus


class CashRegisterRepository(BaseRepository):
    model = CashRegisterSession

    async def get_current(self, tenant_id: int) -> CashRegisterSession | None:
        from sqlalchemy import select
        result = await self.db.scalar(
            select(CashRegisterSession).where(
                CashRegisterSession.tenant_id == tenant_id,
                CashRegisterSession.status == CashRegisterStatus.OPEN,
            )
        )
        return result

    async def get_cash_payments_since(
        self, tenant_id: int, since: str
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
