"""User schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class UserSettings(BaseSchema):
    theme: str = Field(default="system", pattern="^(light|dark|system)$")
    autoplay: bool = False
    history_paused: bool = False


class UserSettingsUpdate(BaseSchema):
    theme: Optional[str] = Field(default=None, pattern="^(light|dark|system)$")
    autoplay: Optional[bool] = None
    history_paused: Optional[bool] = None


class UserProfile(BaseSchema):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    avatar_url: Optional[str] = None
    role: str
    onboarded_at: Optional[datetime] = None
    settings: Dict[str, Any]
    created_at: datetime


class DeleteAccountRequest(BaseSchema):
    confirm_email: EmailStr
