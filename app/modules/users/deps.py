from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.audit import AuditLogger, get_audit_logger
from app.core.database import get_db
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    audit: AuditLogger = Depends(get_audit_logger),
) -> UserService:
    return UserService(user_repo, audit)
