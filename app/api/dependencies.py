from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.core.database import get_db
from app.core.security import get_current_user


def get_audit_logger(db: AsyncSession = Depends(get_db)) -> AuditLogger:
    return AuditLogger(db)


__all__ = ["get_db", "get_current_user", "get_audit_logger"]
