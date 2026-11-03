"""Local catalogue search router."""

from typing import List, Sequence

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.video_repo import VideoRepository
from app.schemas.video import VideoResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=List[VideoResponse], summary="Search cached local catalogue")
async def search(
    q: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[VideoResponse]:
    video_repo = VideoRepository(db)
    videos = await video_repo.search_local(query=q, limit=30)
    items = []
    for v in videos:
        is_liked = await video_repo.is_liked_by_user(current_user.id, v.id)
        items.append(
            VideoResponse.model_validate({**v.__dict__, "is_liked": is_liked, "is_saved": False})
        )
    return items
