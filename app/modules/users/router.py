from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.rate_limit import forgot_password_limiter, activate_limiter
from app.core.security import get_current_user, require_permission
from app.modules.users.deps import get_user_service
from app.core.permissions import PermissionCode
from app.modules.users.model import User
from app.modules.users.schema import (
    ForgotPasswordRequest, ActivationRequest, MessageResponse, ResendActivationRequest, ResetPasswordRequest,
    RoleInfo, TokenResponse, UserAdminResponse, UserAssignRole, UserCreate, UserLogin,
    UserProfileResponse, UserProfileUpdate, UserResponse, UserUpdate,
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


@auth_router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    return await service.get_profile(current_user)


@auth_router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.update_profile(current_user, data)


@auth_router.post("/me/image", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.upload_image(current_user.id, file, current_user.id)


@auth_router.delete("/me/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    await service.delete_image(current_user.id, current_user.id)


@auth_router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> MessageResponse:
    client = request.client.host if request.client else "unknown"
    if not forgot_password_limiter.is_allowed(client):
        return JSONResponse(status_code=429, content={"detail": "Demasiadas solicitudes. Intenta de nuevo mas tarde."})
    forgot_password_limiter.hit(client)
    await service.request_password_reset(data.email)
    return MessageResponse(message="Si el email existe, recibiras instrucciones para restablecer tu contrasena")


@auth_router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    service: UserService = Depends(get_user_service),
) -> MessageResponse:
    await service.reset_password(data.token, data.new_password)
    return MessageResponse(message="Contrasena actualizada correctamente")


@auth_router.post("/activate", response_model=MessageResponse)
async def activate_account(
    data: ActivationRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> MessageResponse:
    client = request.client.host if request.client else "unknown"
    if not activate_limiter.is_allowed(client):
        return JSONResponse(status_code=429, content={"detail": "Demasiadas solicitudes. Intenta de nuevo mas tarde."})
    activate_limiter.hit(client)
    await service.activate_account(data.token)
    return MessageResponse(message="Cuenta activada correctamente")


@auth_router.post("/resend-activation", response_model=MessageResponse)
async def resend_activation(
    data: ResendActivationRequest,
    service: UserService = Depends(get_user_service),
) -> MessageResponse:
    await service.resend_activation(data.email)
    return MessageResponse(message="Si el email existe y la cuenta no esta activada, recibiras un nuevo correo")


# ── Admin CRUD usuarios ──

@users_router.get("/", response_model=PaginatedResponse[UserAdminResponse])
async def list_users(
    pag: dict = PaginationParams,
    email: str | None = Query(default=None, description="Email (único)"),
    filters: dict = FilterParams,
    service: UserService = Depends(get_user_service),
    _perm: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    merged = dict(filters)
    if email is not None:
        merged["email"] = email
    return await service.get_all(page=pag["page"], size=pag["size"], filters=merged or None)


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
    admin: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    return await service.update(user_id, data, admin)


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    admin: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    await service.delete(user_id, admin)


@users_router.get("/{user_id}/roles", response_model=list[RoleInfo])
async def get_user_roles(
    user_id: int,
    service: UserService = Depends(get_user_service),
    _perm: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    return await service.get_user_roles(user_id)


@users_router.post("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    user_id: int,
    data: UserAssignRole,
    service: UserService = Depends(get_user_service),
    _perm: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    await service.assign_role(user_id, data.role_id)


@users_router.post("/{user_id}/image", response_model=UserAdminResponse)
async def upload_user_image(
    user_id: int,
    file: UploadFile = File(...),
    service: UserService = Depends(get_user_service),
    admin: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    return await service.upload_image(user_id, file, admin.id)


@users_router.delete("/{user_id}/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_image(
    user_id: int,
    service: UserService = Depends(get_user_service),
    admin: User = Depends(require_permission(PermissionCode.USERS_MANAGE)),
):
    await service.delete_image(user_id, admin.id)
