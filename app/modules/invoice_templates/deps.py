from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.invoice_templates.repository import InvoiceTemplateRepository
from app.modules.invoice_templates.service import InvoiceTemplateService
from app.modules.payments.repository import PaymentRepository
from app.modules.sales.repository import SaleItemRepository, SaleRepository
from app.modules.shelves.repository import ShelfItemRepository
from app.modules.tenants.repository import TenantRepository


async def get_invoice_template_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> InvoiceTemplateService:
    return InvoiceTemplateService(
        template_repo=InvoiceTemplateRepository(db),
        sale_repo=SaleRepository(db),
        sale_item_repo=SaleItemRepository(db),
        shelf_item_repo=ShelfItemRepository(db),
        payment_repo=PaymentRepository(db),
        tenant_repo=TenantRepository(db),
        audit=audit,
    )
