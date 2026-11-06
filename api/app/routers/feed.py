"""Feed router: Home shelves, For You grid, Category grids, and Shorts feed."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.category_repo import CategoryRepository
from app.repositories.video_repo import VideoRepository
from app.schemas.category import CategoryResponse
from app.schemas.common import CursorPage
from app.schemas.video import VideoResponse

router = APIRouter(prefix="/feed", tags=["Feed"])


class HomeShelf(BaseModel):
    category: CategoryResponse
    videos: List[VideoResponse]


class HomeFeedResponse(BaseModel):
    for_you: List[VideoResponse]
    continue_watching: List[VideoResponse]
    shorts: List[VideoResponse]
    shelves: List[HomeShelf]


@router.get("/home", response_model=HomeFeedResponse, summary="Home feed with shelves and For You")
async def get_home_feed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeFeedResponse:
    cat_repo = CategoryRepository(db)
    video_repo = VideoRepository(db)

    # 1. Fetch user interest categories in chosen order (FR-20)
    interests = await cat_repo.get_user_interests(current_user.id)
    if not interests:
        interests = await cat_repo.list_active()
        interests = interests[:5]

    # 2. Build category shelves (12 videos per shelf)
    shelves = []
    seen_ids = set()
    for cat in interests:
        vids = await video_repo.get_category_videos(cat.id, limit=12)
        valid_items = []
        for v in vids:
            is_liked = await video_repo.is_liked_by_user(current_user.id, v.id)
            valid_items.append(
                VideoResponse.model_validate(
                    {**v.__dict__, "is_liked": is_liked, "is_saved": False}
                )
            )
            seen_ids.add(v.id)
        shelves.append(
            HomeShelf(
                category=CategoryResponse.model_validate(cat),
                videos=valid_items,
            )
        )

    # 3. Continue watching shelf (FR-53)
    continue_vids = await video_repo.get_continue_watching(current_user.id, limit=10)
    cw_items = [
        VideoResponse.model_validate({**v.__dict__, "is_liked": False, "is_saved": False})
        for v in continue_vids
    ]

    # 4. Shorts shelf (FR-23): collect up to 12 actual shorts from interest shelves
    shorts_list = []
    seen_short_ids = set()
    for s in shelves:
        for v in s.videos:
            if v.is_short and v.id not in seen_short_ids:
                shorts_list.append(v)
                seen_short_ids.add(v.id)
                if len(shorts_list) >= 12:
                    break
        if len(shorts_list) >= 12:
            break

    # 5. For you mixed grid (FR-21): interleave categories, deduplicate, exclude shorts & liked/saved
    for_you = []
    seen_for_you_ids = set()
    max_shelf_len = max((len(s.videos) for s in shelves), default=0)
    for idx in range(max_shelf_len):
        for s in shelves:
            if idx < len(s.videos):
                v = s.videos[idx]
                if (
                    not v.is_short
                    and v.id not in seen_for_you_ids
                    and not v.is_liked
                    and not v.is_saved
                ):
                    for_you.append(v)
                    seen_for_you_ids.add(v.id)
                    if len(for_you) >= 12:
                        break
        if len(for_you) >= 12:
            break

    return HomeFeedResponse(
        for_you=for_you,
        continue_watching=cw_items,
        shorts=shorts_list,
        shelves=shelves,
    )


@router.get(
    "/categories/{slug}",
    response_model=CursorPage[VideoResponse],
    summary="Category infinite scroll grid",
)
async def get_category_feed(
    slug: str,
    limit: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CursorPage[VideoResponse]:
    cat_repo = CategoryRepository(db)
    video_repo = VideoRepository(db)

    cat = await cat_repo.get_by_slug(slug)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    videos = await video_repo.get_category_videos(cat.id, limit=limit)
    items = []
    for v in videos:
        is_liked = await video_repo.is_liked_by_user(current_user.id, v.id)
        items.append(
            VideoResponse.model_validate({**v.__dict__, "is_liked": is_liked, "is_saved": False})
        )

    return CursorPage(items=items, next_cursor=None, has_more=False)


@router.get("/shorts", response_model=CursorPage[VideoResponse], summary="Shorts vertical feed")
async def get_shorts_feed(
    limit: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CursorPage[VideoResponse]:
    video_repo = VideoRepository(db)
    # Fetch recent shorts
    stmt = (
        video_repo.db.query(video_repo.db.models.Video) if hasattr(video_repo.db, "query") else None
    )
    # Using repository search or direct query
    from sqlalchemy import desc, select

    from app.models.video import Video

    stmt = (
        select(Video)
        .where(Video.is_short.is_(True))
        .order_by(desc(Video.published_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    videos = res.scalars().all()

    items = []
    for v in videos:
        is_liked = await video_repo.is_liked_by_user(current_user.id, v.id)
        items.append(
            VideoResponse.model_validate({**v.__dict__, "is_liked": is_liked, "is_saved": False})
        )

    return CursorPage(items=items, next_cursor=None, has_more=False)
