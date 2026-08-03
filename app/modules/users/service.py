from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import UploadFile

from app.core.audit import AuditLogger
from app.core.config import settings
from app.core.email import EmailSender
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, UnauthorizedException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.security import create_access_token, hash_password, verify_password
from app.core.storage import generate_filename, get_storage
from app.core.templates import render_template
from app.modules.users.model import User
from app.modules.users.repository import UserRepository
from app.modules.users.schema import (
    RoleInfo, TokenResponse, UserCreate, UserLogin, UserProfileResponse,
    UserProfileUpdate, UserUpdate,
)

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, repo: UserRepository, audit: AuditLogger, email: EmailSender):
        self.repo = repo
        self.audit = audit
        self.email = email

    async def create_user(self, data: UserCreate, actor_id: int) -> User:
        if await self.repo.find_by_email(data.email):
            raise ConflictException("El email ya esta registrado")

        user = await self.repo.create(
            email=data.email,
            hashed_password=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            city=data.city,
            country=data.country,
            is_active=False,
        )
        await self.audit.log_create("User", user.id, actor_id, user)
        await self._send_activation_email(user)
        return user

    async def _send_activation_email(self, user: User) -> None:
        await self.repo.invalidate_user_activations(user.id)

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.ACCOUNT_ACTIVATION_EXPIRE_HOURS
        )
        expires_at = expires_at.replace(tzinfo=None)

        await self.repo.create_activation_token(user.id, token_hash, expires_at)
        await self.audit.log_create("AccountActivation", user.id, user.id, {"action": "activation_token_created"})

        activate_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        html = render_template(
            "emails/account_activation.html",
            {
                "user_name": user.first_name or user.email,
                "activate_url": activate_url,
                "expires_hours": settings.ACCOUNT_ACTIVATION_EXPIRE_HOURS,
                "current_year": datetime.utcnow().year,
            },
        )

        try:
            await self.email.send(user.email, "Activa tu cuenta", html)
        except Exception as e:
            logger.error("Failed to send activation email to %s: %s", user.email, e)
            from app.core.exceptions import AppException
            raise AppException("No se pudo enviar el email de activacion. Por favor intenta de nuevo.", 500)

    async def activate_account(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        activation = await self.repo.find_valid_activation(token_hash)
        if not activation:
            raise ValidationException("Token invalido o expirado")

        user = await self.repo.get_by_id(activation.user_id)
        if not user:
            raise ValidationException("Token invalido o expirado")

        if user.is_active:
            raise ValidationException("La cuenta ya esta activada")

        await self.repo.update(user, is_active=True)
        await self.repo.invalidate_user_activations(user.id)

        await self.audit.log_update("User", user.id, user.id, {"is_active": True})

    async def resend_activation(self, email: str) -> None:
        user = await self.repo.find_by_email(email)
        if not user:
            return

        if user.is_active:
            return

        await self._send_activation_email(user)

    async def authenticate(self, credentials: UserLogin) -> TokenResponse:
        user = await self.repo.find_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise UnauthorizedException("Email o contrasena incorrectos")
        if not user.is_active:
            raise ForbiddenException("Cuenta no activada. Revisa tu correo para activarla.")
        return TokenResponse(access_token=create_access_token(user.id, user.token_version, user.tenant_id))

    async def pin_login(self, email: str, pin: str) -> TokenResponse:
        user = await self.repo.find_by_email(email)
        if not user or not user.pin:
            raise UnauthorizedException("Credenciales invalidas")
        if not verify_password(pin, user.pin):
            raise UnauthorizedException("Credenciales invalidas")
        if not user.is_active:
            raise ForbiddenException("Cuenta no activada")
        return TokenResponse(access_token=create_access_token(user.id, user.token_version, user.tenant_id))

    async def set_pin(self, user_id: int, pin: str, actor_id: int) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")
        await self.repo.update(user, pin=hash_password(pin))
        await self.audit.log_update("User", user.id, actor_id, {"pin": "set"})

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[User]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")
        return user

    async def get_user_roles(self, user_id: int) -> list[RoleInfo]:
        if not await self.repo.get_by_id(user_id):
            raise NotFoundException("Usuario no encontrado")
        roles = await self.repo.get_user_roles(user_id)
        return [RoleInfo(id=r.id, tenant_id=r.tenant_id, name=r.name) for r in roles]

    async def assign_role(self, user_id: int, role_id: int) -> None:
        from app.modules.roles.model import Role
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")
        role = await Role.get_id(self.repo.db, role_id, tenant_id=user.tenant_id)
        if not role:
            raise NotFoundException("Rol no encontrado")
        if user.tenant_id is not None and user.tenant_id != role.tenant_id:
            raise ValidationException("Usuario y rol deben pertenecer al mismo tenant")
        await self.repo.assign_role(user_id, role_id)

    async def get_profile(self, user: User) -> UserProfileResponse:
        roles = await self.repo.get_user_roles(user.id)
        permissions = await self.repo.get_user_permissions(user.id, user.is_super_admin)

        return UserProfileResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            city=user.city,
            country=user.country,
            is_active=user.is_active,
            is_super_admin=user.is_super_admin,
            tenant_id=user.tenant_id,
            image_path=user.image_path,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[RoleInfo(id=r.id, tenant_id=r.tenant_id, name=r.name) for r in roles],
            permissions=permissions,
        )

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))
        user = await self.repo.update(user, **update_data)
        await self.audit.log_update("User", user.id, user.id, user)
        return user

    async def update(self, user_id: int, data: UserUpdate, admin_user: User) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] != user.email:
            existing = await self.repo.find_by_email(update_data["email"])
            if existing and existing.id != user_id:
                raise ConflictException("El email ya esta en uso")

        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        user = await self.repo.update(user, **update_data)
        await self.audit.log_update("User", user.id, admin_user.id, user)
        return user

    async def delete(self, user_id: int, admin_user: User) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")

        if await self.repo.has_sales(user_id):
            raise ConflictException(
                "No se puede eliminar un usuario con historial de ventas"
            )

        if await self.repo.has_orders(user_id):
            raise ConflictException(
                "No se puede eliminar un usuario con historial de pedidos"
            )

        if user.image_path:
            storage = get_storage()
            await storage.delete(user.image_path)

        await self.audit.log_delete("User", user.id, admin_user.id, user)
        await self.repo.delete(user)

    async def upload_image(self, user_id: int, file: UploadFile, actor_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")

        storage = get_storage()
        if user.image_path:
            await storage.delete(user.image_path)

        filename = generate_filename(f"user_{user_id}", file.filename or "avatar.jpg")
        relative_path = f"users/{filename}"
        await storage.upload(file, relative_path)

        await self.repo.update(user, image_path=relative_path)
        await self.audit.log_update("User", user.id, actor_id, {"image_path": relative_path})
        return user

    async def request_password_reset(self, email: str) -> None:
        user = await self.repo.find_by_email(email)
        if not user or not user.is_active:
            await asyncio.sleep(random.uniform(0.1, 0.3))
            return

        await self.repo.invalidate_user_tokens(user.id)

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        expires_at = expires_at.replace(tzinfo=None)

        await self.repo.create_reset_token(user.id, token_hash, expires_at)
        await self.audit.log_create("PasswordResetToken", user.id, user.id, {"action": "reset_token_created"})

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        html = render_template(
            "emails/password_reset.html",
            {
                "user_name": user.first_name or user.email,
                "reset_url": reset_url,
                "expires_minutes": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
                "current_year": datetime.utcnow().year,
            },
        )

        try:
            await self.email.send(user.email, "Recuperacion de contrasena", html)
        except Exception as e:
            logger.error("Failed to send reset email to %s: %s", user.email, e)

    async def reset_password(self, token: str, new_password: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset_token = await self.repo.find_valid_token(token_hash)
        if not reset_token:
            raise ValidationException("Token invalido o expirado")

        user = await self.repo.get_by_id(reset_token.user_id)
        if not user:
            raise ValidationException("Token invalido o expirado")

        update_data = {"hashed_password": hash_password(new_password), "token_version": user.token_version + 1}
        if not user.is_active:
            update_data["is_active"] = True

        await self.repo.update(user, **update_data)
        await self.repo.invalidate_user_tokens(user.id)

        await self.audit.log_update("User", user.id, user.id, {"password": "changed", "token_version_incremented": True})

    async def delete_image(self, user_id: int, actor_id: int) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")

        if user.image_path:
            storage = get_storage()
            await storage.delete(user.image_path)
            await self.repo.update(user, image_path=None)
            await self.audit.log_update("User", user.id, actor_id, {"image_path": None})
