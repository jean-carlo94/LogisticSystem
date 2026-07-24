from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException

if TYPE_CHECKING:
    from app.modules.users.model import User

bearer_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def get_current_user(
    token: str = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    from app.modules.users.model import User

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str | None = payload.get("sub")
    except JWTError:
        raise UnauthorizedException("Credenciales invalidas o expiradas")

    if user_id is None:
        raise UnauthorizedException("Credenciales invalidas o expiradas")

    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedException("Credenciales invalidas o expiradas")
    return user


def require_permission(permission_code: str):
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_super_admin:
            return current_user

        from sqlalchemy import select
        from app.modules.roles.model import Permission, RolePermission, UserRole

        result = await db.scalar(
            select(Permission).join(
                RolePermission, RolePermission.permission_id == Permission.id
            ).join(
                UserRole, UserRole.role_id == RolePermission.role_id
            ).where(
                UserRole.user_id == current_user.id,
                Permission.code == permission_code,
            )
        )
        if not result:
            raise ForbiddenException(f"No tienes permiso: {permission_code.value}")
        return current_user

    return dependency
