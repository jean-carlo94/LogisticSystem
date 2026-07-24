from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(..., examples=["usuario@email.com"])
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["usuario@email.com"])
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None


class UserAdminResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_super_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}
