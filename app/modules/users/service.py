from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, UnauthorizedException
from app.core.pagination import PaginatedResult
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users.model import User
from app.modules.users.repository import UserRepository
from app.modules.users.schema import (
    RoleInfo, TokenResponse, UserCreate, UserLogin, UserProfileUpdate, UserUpdate,
)


class UserService:
    def __init__(self, repo: UserRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def register(self, user_in: UserCreate) -> User:
        if await self.repo.find_by_email(user_in.email):
            raise ConflictException("El email ya esta registrado")

        user = await self.repo.create(
            email=user_in.email,
            hashed_password=hash_password(user_in.password),
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            phone=user_in.phone,
            city=user_in.city,
            country=user_in.country,
        )
        await self.audit.log_create("User", user.id, user.id, user)
        return user

    async def authenticate(self, credentials: UserLogin) -> TokenResponse:
        user = await self.repo.find_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise UnauthorizedException("Email o contrasena incorrectos")
        if not user.is_active:
            raise ForbiddenException("Usuario inactivo")
        return TokenResponse(access_token=create_access_token(user.id))

    async def get_all(self, page: int = 1, size: int = 20) -> PaginatedResult[User]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size)
        return PaginatedResult.of(list(items), total, page, size)

    async def get_by_id(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("Usuario no encontrado")
        return user

    async def get_user_roles(self, user_id: int) -> list[RoleInfo]:
        if not await self.repo.get_by_id(user_id):
            raise NotFoundException("Usuario no encontrado")
        roles = await self.repo.get_user_roles(user_id)
        return [RoleInfo(id=r.id, name=r.name) for r in roles]

    async def assign_role(self, user_id: int, role_id: int) -> None:
        if not await self.repo.get_by_id(user_id):
            raise NotFoundException("Usuario no encontrado")
        if not await self.repo.role_exists(role_id):
            raise NotFoundException("Rol no encontrado")
        await self.repo.assign_role(user_id, role_id)

    async def get_profile(self, user: User) -> dict:
        roles = await self.repo.get_user_roles(user.id)
        permissions = await self.repo.get_user_permissions(user.id, user.is_super_admin)

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "city": user.city,
            "country": user.country,
            "is_active": user.is_active,
            "is_super_admin": user.is_super_admin,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": [RoleInfo(id=r.id, name=r.name) for r in roles],
            "permissions": permissions,
        }

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

        await self.audit.log_delete("User", user.id, admin_user.id, user)
        await self.repo.delete(user)
