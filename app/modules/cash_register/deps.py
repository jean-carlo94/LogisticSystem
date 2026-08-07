from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.cash_register.repository import CashRegisterCRUDRepository, CashRegisterRepository
from app.modules.cash_register.service import CashRegisterCRUDService, CashRegisterService


async def get_cash_register_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> CashRegisterService:
    return CashRegisterService(
        CashRegisterRepository(db),
        audit,
    )


async def get_cash_register_crud_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> CashRegisterCRUDService:
    return CashRegisterCRUDService(
        CashRegisterCRUDRepository(db),
        audit,
    )
