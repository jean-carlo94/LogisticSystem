from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.storage import get_image_url


class UserCreate(BaseModel):
    email: EmailStr = Field(..., examples=["usuario@email.com"])
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None


class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["usuario@email.com"])
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    is_active: bool
    image_path: str | None = None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_image_url(self) -> "UserResponse":
        self.image_url = get_image_url(self.image_path)
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    is_active: bool | None = None


class UserAdminResponse(BaseModel):
    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    is_active: bool
    is_super_admin: bool
    image_path: str | None = None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_image_url(self) -> "UserAdminResponse":
        self.image_url = get_image_url(self.image_path)
        return self


class RoleInfo(BaseModel):
    id: int
    name: str


class UserProfileResponse(BaseModel):
    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    is_active: bool
    is_super_admin: bool
    image_path: str | None = None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime
    roles: list[RoleInfo] = []
    permissions: list[str] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_image_url(self) -> "UserProfileResponse":
        self.image_url = get_image_url(self.image_path)
        return self


class UserProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserAssignRole(BaseModel):
    role_id: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ActivationRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=256)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=6, max_length=128)


class ResendActivationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str
