from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.categories.repository import CategoryRepository
from app.modules.categories.service import CategoryService


async def get_category_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> CategoryService:
    return CategoryService(CategoryRepository(db), audit)
