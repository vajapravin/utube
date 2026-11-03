"""Seed categories catalogue from seed/categories.yaml."""

import asyncio
from pathlib import Path

import yaml
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.category import Category


async def seed_categories() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    seed_file = Path(__file__).resolve().parents[3] / "seed" / "categories.yaml"
    if not seed_file.exists():
        # Fallback to local seed path
        seed_file = Path("seed/categories.yaml")

    with open(seed_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    categories = data.get("categories", [])
    async with session_factory() as session:
        for cat in categories:
            stmt = (
                insert(Category)
                .values(
                    slug=cat["slug"],
                    name=cat["name"],
                    icon=cat["icon"],
                    yt_category_id=cat.get("yt_category_id"),
                    seed_queries=cat.get("seed_queries", []),
                    sort_order=cat.get("sort_order", 0),
                    is_active=True,
                )
                .on_conflict_do_update(
                    index_elements=["slug"],
                    set_={
                        "name": cat["name"],
                        "icon": cat["icon"],
                        "yt_category_id": cat.get("yt_category_id"),
                        "seed_queries": cat.get("seed_queries", []),
                        "sort_order": cat.get("sort_order", 0),
                    },
                )
            )
            await session.execute(stmt)
        await session.commit()
    print(f"Successfully seeded {len(categories)} categories.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_categories())
