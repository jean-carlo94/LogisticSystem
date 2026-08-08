from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
import hashlib
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.permissions import PermissionCode
from app.core.tenant import current_tenant_id

if TYPE_CHECKING:
    from app.modules.users.model import User

bearer_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int, token_version: int = 0, tenant_id: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire, "ver": token_version}
    if tenant_id is not None:
        payload["tid"] = tenant_id
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def get_current_user(
    token: str | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    from app.modules.users.model import User

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id: str | None = payload.get("sub")
            token_ver: int = payload.get("ver", 0)
        except JWTError:
            raise UnauthorizedException("Credenciales invalidas o expiradas")

        if user_id is None:
            raise UnauthorizedException("Credenciales invalidas o expiradas")

        user = await db.get(User, int(user_id))
        if user is None or not user.is_active:
            raise UnauthorizedException("Credenciales invalidas o expiradas")
        if user.token_version != token_ver:
            raise UnauthorizedException("Sesion invalida. La contrasena fue cambiada. Inicia sesion de nuevo.")

        if not user.is_super_admin and user.tenant_id is not None:
            from app.modules.tenants.model import Tenant
            tenant = await db.get(Tenant, user.tenant_id)
            if not tenant or not tenant.is_active:
                raise ForbiddenException("Este tenant está deshabilitado")
            current_tenant_id.set(user.tenant_id)

        return user

    if x_api_key:
        from app.modules.api_keys.model import ApiKey
        key_hash = hash_api_key(x_api_key)
        key = await db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if not key or not key.is_active:
            raise UnauthorizedException("API Key invalida o inactiva")
        if key.expires_at and key.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException("API Key expirada")
        from app.modules.tenants.model import Tenant
        tenant = await db.get(Tenant, key.tenant_id)
        if not tenant or not tenant.is_active:
            raise ForbiddenException("Este tenant está deshabilitado")
        current_tenant_id.set(key.tenant_id)
        await db.execute(
            update(ApiKey).where(ApiKey.id == key.id).values(last_used_at=datetime.now(timezone.utc))
        )
        await db.commit()
        synthetic_user = User(
            email=f"apikey+{key.id}@internal",
            hashed_password="",
            first_name="",
            is_active=True,
            is_super_admin=False,
            tenant_id=key.tenant_id,
        )
        setattr(synthetic_user, "_api_key", key)
        synthetic_user.id = 0
        synthetic_user.token_version = 0
        return synthetic_user

    raise UnauthorizedException("Autenticación requerida (Bearer token o X-Api-Key)")


def require_permission(permission_code: PermissionCode):
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        _tenant: int | None = Depends(_tenant_context),
    ) -> User:
        if current_user.is_super_admin:
            return current_user

        api_key = getattr(current_user, "_api_key", None)
        if api_key is not None:
            if permission_code.value not in (api_key.permissions or []):
                raise ForbiddenException(f"API Key no tiene permiso: {permission_code.value}")
            return current_user

        from app.modules.roles.model import Permission, Role, RolePermission, UserRole

        result = await db.scalar(
            select(Permission).join(
                RolePermission, RolePermission.permission_id == Permission.id
            ).join(
                Role, Role.id == RolePermission.role_id
            ).join(
                UserRole, UserRole.role_id == Role.id
            ).where(
                UserRole.user_id == current_user.id,
                Permission.code == permission_code,
            )
        )
        if not result:
            raise ForbiddenException(f"No tienes permiso: {permission_code.value}")
        return current_user

    return dependency


async def _tenant_context(
    current_user: User = Depends(get_current_user),
    x_tenant: str | None = Header(default=None, alias="X-Tenant"),
) -> int | None:
    from app.core.tenant import resolve_tenant
    return await resolve_tenant(current_user, x_tenant)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def get_current_api_key(
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    db: AsyncSession = Depends(get_db),
) -> "ApiKey":
    from app.modules.api_keys.model import ApiKey

    if not x_api_key:
        raise UnauthorizedException("API Key requerida (header X-Api-Key)")

    key_hash = hash_api_key(x_api_key)
    key = await db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))

    if not key or not key.is_active:
        raise UnauthorizedException("API Key invalida o inactiva")

    if key.expires_at and key.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedException("API Key expirada")

    current_tenant_id.set(key.tenant_id)

    from sqlalchemy import update
    await db.execute(
        update(ApiKey).where(ApiKey.id == key.id).values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return key


def require_module(module_name: str):
    async def dependency(
        x_tenant: str | None = Header(default=None, alias="X-Tenant"),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        from sqlalchemy import select
        from app.core.tenant import current_tenant_id
        from app.modules.tenant_config.model import TenantConfig

        tid = current_tenant_id.get()
        if tid is None:
            return

        config = await db.scalar(
            select(TenantConfig).where(TenantConfig.tenant_id == tid)
        )
        if config and module_name not in (config.modules_enabled or []):
            raise ForbiddenException(f"Módulo '{module_name}' no está habilitado para este tenant")

    return dependency


async def require_cash_register(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int | None:
    from app.core.tenant import current_tenant_id
    from app.modules.tenant_config.model import TenantConfig

    tid = current_tenant_id.get()
    if tid is None:
        return None

    config = await db.scalar(
        select(TenantConfig).where(TenantConfig.tenant_id == tid)
    )
    if not config or "cash_register" not in (config.modules_enabled or []):
        return None

    from app.modules.cash_register.repository import CashRegisterRepository
    repo = CashRegisterRepository(db)
    session = await repo.get_open_for_user(current_user.id)
    if not session:
        raise ConflictException("Debe abrir una caja primero")

    return session.id
