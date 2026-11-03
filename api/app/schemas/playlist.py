"""Playlist schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.video import VideoResponse


class PlaylistCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    visibility: str = Field(default="private", pattern="^(private|unlisted)$")


class PlaylistUpdate(BaseSchema):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    visibility: Optional[str] = Field(default=None, pattern="^(private|unlisted)$")


class PlaylistItemResponse(BaseSchema):
    id: uuid.UUID
    video: VideoResponse
    position: str
    added_at: datetime


class PlaylistResponse(BaseSchema):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: Optional[str] = None
    visibility: str
    system_kind: Optional[str] = None
    item_count: int = 0
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PlaylistItemAdd(BaseSchema):
    youtube_id: str


class PlaylistItemMove(BaseSchema):
    prev_position: Optional[str] = None
    next_position: Optional[str] = None
