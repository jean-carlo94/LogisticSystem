from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from app.core.storage import get_image_url


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_email: str | None = Field(default=None, max_length=255)
    admin_password: str | None = Field(default=None, min_length=6)


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    logo_path: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def logo_url(self) -> str | None:
        return get_image_url(self.logo_path)
