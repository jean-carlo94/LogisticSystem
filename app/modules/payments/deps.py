from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.payments.repository import PaymentMethodRepository, PaymentRepository
from app.modules.payments.service import PaymentMethodService, PaymentService
from app.modules.sales.repository import SaleRepository


async def get_payment_method_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> PaymentMethodService:
    return PaymentMethodService(PaymentMethodRepository(db), audit)


async def get_payment_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> PaymentService:
    return PaymentService(
        PaymentRepository(db),
        SaleRepository(db),
        PaymentMethodRepository(db),
        audit,
    )
