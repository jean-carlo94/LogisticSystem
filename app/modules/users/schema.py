from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


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
        if self.image_path:
            self.image_url = f"/static/{self.image_path}"
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
        if self.image_path:
            self.image_url = f"/static/{self.image_path}"
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
        if self.image_path:
            self.image_url = f"/static/{self.image_path}"
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
