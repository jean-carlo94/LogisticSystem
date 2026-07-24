import json

from fastapi import HTTPException, status

from app.core.audit import AuditLogger
from app.core.security import create_access_token, verify_password
from app.modules.users.model import User
from app.modules.users.repository import UserRepository
from app.modules.users.schema import TokenResponse, UserCreate, UserLogin


class UserService:
    def __init__(self, user_repo: UserRepository, audit: AuditLogger):
        self.user_repo = user_repo
        self.audit = audit

    def register(self, user_in: UserCreate) -> User:
        existing = self.user_repo.get_by_email(user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya esta registrado",
            )

        from app.core.security import hash_password

        user = self.user_repo.create(user_in, hash_password(user_in.password))
        self.audit.log_create("User", user.id, user.id, json.dumps({"email": user.email}))
        return user

    def authenticate(self, credentials: UserLogin) -> TokenResponse:
        user = self.user_repo.get_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contrasena incorrectos",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo",
            )

        return TokenResponse(access_token=create_access_token(user.id))

    def get_current_user(self, user_id: int) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        return user
