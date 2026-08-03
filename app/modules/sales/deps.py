from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.service import CustomerService
from app.modules.payments.repository import PaymentRepository
from app.modules.products.repository import ProductRepository
from app.modules.sales.repository import SaleItemRepository, SaleRepository
from app.modules.sales.service import SaleService
from app.modules.shelves.repository import ShelfItemRepository, ShelfRepository
from app.modules.tenants.repository import TenantRepository


async def get_sale_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> SaleService:
    return SaleService(
        SaleRepository(db),
        SaleItemRepository(db),
        ShelfItemRepository(db),
        ShelfRepository(db),
        ProductRepository(db),
        CustomerService(CustomerRepository(db), audit),
        audit,
        PaymentRepository(db),
        TenantRepository(db),
    )
