from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.modules.users.deps import get_user_service
from app.modules.users.model import User
from app.modules.users.schema import TokenResponse, UserCreate, UserLogin, UserResponse
from app.modules.users.service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await service.register(user_in)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    service: UserService = Depends(get_user_service),
) -> TokenResponse:
    return await service.authenticate(credentials)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return current_user
