from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.service import CustomerService


async def get_customer_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> CustomerService:
    return CustomerService(CustomerRepository(db), audit)
