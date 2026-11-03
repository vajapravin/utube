"""Channel and curation schemas."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class ChannelPlan(BaseSchema):
    queries: List[str] = Field(min_length=3, max_length=8)
    must_include_terms: List[str] = Field(default_factory=list)
    exclude_terms: List[str] = Field(default_factory=list)
    language: str = "en"
    region: str = "GB"
    min_duration_s: Optional[int] = None
    max_duration_s: Optional[int] = None
    published_after: Optional[str] = None
    safe_search: str = Field(default="moderate", pattern="^(strict|moderate|none)$")
    want_shorts: bool = True
    want_videos: bool = True


class ChannelCreate(BaseSchema):
    name: str = Field(min_length=3, max_length=60)
    handle: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)
    prompt: str = Field(min_length=20, max_length=2000)
    visibility: str = Field(default="private", pattern="^(private|unlisted|public)$")
    banner_style: Optional[str] = Field(default=None, max_length=255)
    category_ids: List[uuid.UUID] = Field(default_factory=list)


class ChannelUpdate(BaseSchema):
    name: Optional[str] = Field(default=None, min_length=3, max_length=60)
    description: Optional[str] = Field(default=None, max_length=500)
    prompt: Optional[str] = Field(default=None, min_length=20, max_length=2000)
    visibility: Optional[str] = Field(default=None, pattern="^(private|unlisted|public)$")
    banner_style: Optional[str] = Field(default=None, max_length=255)
    recurate: bool = False


class ChannelResponse(BaseSchema):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    handle: str
    description: Optional[str] = None
    prompt: Optional[str] = None  # Shown to owner only
    visibility: str
    banner_style: Optional[str] = None
    status: str
    video_count: int = 0
    short_count: int = 0
    last_curated_at: Optional[datetime] = None
    created_at: datetime
    is_owner: bool = False


class PreviewPlanRequest(BaseSchema):
    prompt: str = Field(min_length=20, max_length=2000)
