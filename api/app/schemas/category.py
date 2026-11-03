"""Category schemas."""

import uuid
from typing import List, Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class CategoryResponse(BaseSchema):
    id: uuid.UUID
    slug: str
    name: str
    icon: str
    yt_category_id: Optional[str] = None
    sort_order: int


class UserInterestsUpdate(BaseSchema):
    category_ids: List[uuid.UUID] = Field(min_length=3, max_length=10)
