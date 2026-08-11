import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource: str
    action: str
    description: str | None
    created_at: datetime


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class RoleAssignmentRequest(BaseModel):
    role_id: uuid.UUID


class PermissionAssignmentRequest(BaseModel):
    permission_id: uuid.UUID
