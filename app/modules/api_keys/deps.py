from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.api_keys.repository import ApiKeyRepository
from app.modules.api_keys.service import ApiKeyService


async def get_api_key_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ApiKeyService:
    return ApiKeyService(ApiKeyRepository(db), audit)
