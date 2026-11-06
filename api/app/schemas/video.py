"""Video schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field

from app.schemas.common import BaseSchema


class VideoResponse(BaseSchema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    youtube_id: str
    title: str
    description: Optional[str] = None
    source_channel_id: Optional[str] = None
    source_channel_title: Optional[str] = None
    duration_s: int
    is_short: bool
    aspect: str
    thumbnails: Dict[str, Any]
    published_at: datetime
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    is_liked: bool = False
    is_saved: bool = False


class ProgressUpdate(BaseSchema):
    progress_s: int = Field(ge=0)
    duration_s: int = Field(default=0, ge=0)

