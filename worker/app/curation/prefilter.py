"""Deterministic candidate pre-filtering (FR-33 step 3 - zero LLM tokens)."""

from typing import Any, Dict, List, Set


def prefilter_candidates(
    candidates: List[Dict[str, Any]],
    exclude_terms: List[str],
    min_duration_s: int | None = None,
    max_duration_s: int | None = None,
    max_candidates: int = 150,
) -> List[Dict[str, Any]]:
    """Deterministically filter candidates based on keywords, duration bounds, and uniqueness.

    Limits candidate pool to max_candidates (default 150).
    """
    seen_ids: Set[str] = set()
    filtered: List[Dict[str, Any]] = []

    lower_exclusions = [t.lower().strip() for t in exclude_terms if t.strip()]

    for c in candidates:
        video_id = c.get("id") or c.get("youtube_id")
        if not video_id or video_id in seen_ids:
            continue

        title = c.get("title", "").lower()
        desc = c.get("description", "").lower()
        full_text = f"{title} {desc}"

        # 1. Exclude terms check
        if any(term in full_text for term in lower_exclusions):
            continue

        # 2. Duration bounds check
        duration_s = c.get("duration_s", 0)
        if min_duration_s is not None and duration_s < min_duration_s:
            continue
        if max_duration_s is not None and duration_s > max_duration_s:
            continue

        # 3. Made for kids check
        if c.get("made_for_kids", False):
            continue

        seen_ids.add(video_id)
        filtered.append(c)

        if len(filtered) >= max_candidates:
            break

    return filtered
