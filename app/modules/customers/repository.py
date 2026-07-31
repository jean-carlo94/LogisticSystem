from sqlalchemy import select

from app.core.repository import BaseRepository
from app.core.tenant import current_tenant_id
from app.modules.customers.model import Customer


class CustomerRepository(BaseRepository):
    model = Customer

    async def find_by_document(self, document: str) -> Customer | None:
        tid = current_tenant_id.get()
        stmt = select(Customer).where(Customer.document == document)
        if tid is not None:
            stmt = stmt.where(Customer.tenant_id == tid)
        return await self.db.scalar(stmt)

    async def find_by_email(self, email: str) -> Customer | None:
        tid = current_tenant_id.get()
        stmt = select(Customer).where(Customer.email == email)
        if tid is not None:
            stmt = stmt.where(Customer.tenant_id == tid)
        return await self.db.scalar(stmt)
