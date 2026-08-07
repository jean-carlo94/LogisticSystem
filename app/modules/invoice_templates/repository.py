from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.invoice_templates.model import InvoiceTemplate


class InvoiceTemplateRepository(BaseRepository):
    model = InvoiceTemplate

    async def get_by_tenant(self, tenant_id: int) -> InvoiceTemplate | None:
        result = await self.db.scalar(
            select(InvoiceTemplate).where(InvoiceTemplate.tenant_id == tenant_id)
        )
        return result
