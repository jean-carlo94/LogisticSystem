from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.taxes.repository import TaxRepository
from app.modules.taxes.service import TaxService


async def get_tax_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> TaxService:
    return TaxService(TaxRepository(db), audit)
