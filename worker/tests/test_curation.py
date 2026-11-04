import json
from pathlib import Path

import pytest
from mytube_shared.prefilter import prefilter_candidates

from app.providers.llm import FakeLLMProvider
from app.schemas.channel import ChannelPlan


@pytest.fixture
def golden_candidates():
    p = (
        Path(__file__).resolve().parent.parent.parent
        / "seed"
        / "fixtures"
        / "youtube"
        / "candidates.json"
    )
    with open(p) as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_llm_plan_generation():
    """Verify (a) prompt produces ChannelPlan with queries and duration bounds."""
    provider = FakeLLMProvider()
    plan = await provider.generate_structured(
        system="Turn prompt into ChannelPlan",
        user="ESP32 tutorials under 25 min",
        schema=ChannelPlan,
    )
    assert isinstance(plan, ChannelPlan)
    assert any("esp32" in q.lower() for q in plan.queries)
    assert plan.max_duration_s is not None and plan.max_duration_s <= 1500
    assert "clickbait" in plan.exclude_terms


def test_deterministic_prefilter_duration_and_exclusions(golden_candidates):
    """Verify (b) pre-filter drops candidates violating max duration or exclude terms."""
    # The fixture has:
    # 1. esp32_tut_01: 840s (keep)
    # 2. esp32_short_01: 45s (keep)
    # 3. injection_candidate_01: 300s (keep unless excluded)
    # 4. too_long_tut_01: 14400s (4 hours - MUST be dropped by max_duration_s=1200)

    filtered = prefilter_candidates(
        candidates=golden_candidates,
        exclude_terms=["admin", "bootcamp"],
        max_duration_s=1200,
    )

    filtered_ids = {c["id"] for c in filtered}
    # 4-hour video must be dropped
    assert "too_long_tut_01" not in filtered_ids
    # "admin" term video must be dropped
    assert "injection_candidate_01" not in filtered_ids
    # Valid esp32 videos retained
    assert "esp32_tut_01" in filtered_ids
    assert "esp32_short_01" in filtered_ids


def test_shorts_duration_classification(golden_candidates):
    """Verify (d) items <= 180s are classified as shorts."""
    short_item = next(c for c in golden_candidates if c["id"] == "esp32_short_01")
    long_item = next(c for c in golden_candidates if c["id"] == "esp32_tut_01")

    assert short_item["duration_s"] <= 180
    assert short_item["is_short"] is True
    assert long_item["duration_s"] > 180
    assert long_item["is_short"] is False
