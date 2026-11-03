"""Categories catalogue router."""

from typing import List, Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.repositories.category_repo import CategoryRepository
from app.schemas.category import CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse], summary="List all active categories")
async def list_categories(db: AsyncSession = Depends(get_db)) -> Sequence[CategoryResponse]:
    cat_repo = CategoryRepository(db)
    categories = await cat_repo.list_active()
    return [CategoryResponse.model_validate(c) for c in categories]
