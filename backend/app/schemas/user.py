"""Safe user response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
