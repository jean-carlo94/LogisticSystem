from fastapi import APIRouter, Depends, status

from app.core.pagination import PaginatedResponse
from app.core.security import get_current_user, require_permission
from app.modules.users.deps import get_user_service
from app.core.permissions import PermissionCode
from app.modules.users.model import User
from app.modules.users.schema import (
    TokenResponse, UserAdminResponse, UserCreate, UserLogin, UserResponse, UserUpdate,
)
from app.modules.users.service import UserService

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


# ── Auth (público + autenticado) ──

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.register(user_in)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    service: UserService = Depends(get_user_service),
) -> TokenResponse:
    return await service.authenticate(credentials)


@auth_router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return current_user


# ── Admin CRUD usuarios ──

@users_router.get("/", response_model=PaginatedResponse[UserAdminResponse])
async def list_users(
    service: UserService = Depends(get_user_service),
    _perm: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    return await service.get_all()


@users_router.get("/{user_id}", response_model=UserAdminResponse)
async def retrieve_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    _perm: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    return await service.get_by_id(user_id)


@users_router.put("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
    admin: User = Depends(require_permission("users_manage")),
):
    return await service.update(user_id, data, admin)


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    admin: User = Depends(require_permission("users_manage")),
):
    await service.delete(user_id, admin)
