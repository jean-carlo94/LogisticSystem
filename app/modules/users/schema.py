from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, model_validator

from app.core.storage import get_image_url


class UserCreate(BaseModel):
    email: EmailStr = Field(..., max_length=255, examples=["usuario@email.com"])
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr = Field(..., max_length=255, examples=["usuario@email.com"])
    password: str = Field(..., min_length=6, max_length=128)


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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def image_url(self) -> str | None:
        return get_image_url(self.image_path)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def image_url(self) -> str | None:
        return get_image_url(self.image_path)


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
    created_at: datetime
    updated_at: datetime
    roles: list[RoleInfo] = []
    permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def image_url(self) -> str | None:
        return get_image_url(self.image_path)


class UserProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserAssignRole(BaseModel):
    role_id: int = Field(..., gt=0)


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
