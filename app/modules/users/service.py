from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users.model import User
from app.modules.users.repository import UserRepository
from app.modules.users.schema import TokenResponse, UserCreate, UserLogin


class UserService:
    def __init__(self, repo: UserRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def register(self, user_in: UserCreate) -> User:
        if await self.repo.find_by_email(user_in.email):
            raise ConflictException("El email ya esta registrado")

        user = await self.repo.create(
            email=user_in.email, hashed_password=hash_password(user_in.password),
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
