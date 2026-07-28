from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.core.email import EmailSender
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


async def get_user_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    email: EmailSender = Depends(EmailSender),
) -> UserService:
    return UserService(UserRepository(db), audit, email)
