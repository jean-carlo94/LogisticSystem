from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.shelves.repository import ShelfItemRepository, ShelfRepository
from app.modules.shelves.service import ShelfService


async def get_shelf_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ShelfService:
    return ShelfService(ShelfRepository(db), ShelfItemRepository(db), audit)
