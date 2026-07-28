from datetime import datetime

from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: int
    code: str
    description: str | None = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[int] = Field(..., min_length=1)


class AssignRoleRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    role_id: int = Field(..., gt=0)
