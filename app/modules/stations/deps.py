from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.service import CustomerService
from app.modules.sales.deps import get_sale_service
from app.modules.sales.service import SaleService
from app.modules.shelves.repository import ShelfItemRepository
from app.modules.stations.repository import (
    StationRepository,
    StationSessionRepository,
    StationSessionItemRepository,
)
from app.modules.stations.service import StationService


async def get_station_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    sale_service: SaleService = Depends(get_sale_service),
) -> StationService:
    return StationService(
        StationRepository(db),
        StationSessionRepository(db),
        StationSessionItemRepository(db),
        ShelfItemRepository(db),
        audit,
        sale_service,
        CustomerService(CustomerRepository(db), audit),
    )
