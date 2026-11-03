"""Unit tests for deterministic curation pre-filter."""

from mytube_shared.prefilter import prefilter_candidates


def test_prefilter_excludes_negative_keywords():
    candidates = [
        {
            "id": "1",
            "title": "Great Python Tutorial",
            "description": "Learn clean code",
            "duration_s": 300,
        },
        {
            "id": "2",
            "title": "SHOCKING REACTION Clickbait",
            "description": "Reacting to things",
            "duration_s": 300,
        },
        {
            "id": "3",
            "title": "Advanced Python",
            "description": "Deep dive into descriptors",
            "duration_s": 400,
        },
    ]

    filtered = prefilter_candidates(
        candidates=candidates,
        exclude_terms=["reaction", "clickbait"],
    )

    ids = [c["id"] for c in filtered]
    assert "1" in ids
    assert "3" in ids
    assert "2" not in ids


def test_prefilter_enforces_duration_bounds():
    candidates = [
        {"id": "1", "title": "Too short", "description": "", "duration_s": 30},
        {"id": "2", "title": "Just right", "description": "", "duration_s": 600},
        {"id": "3", "title": "Too long", "description": "", "duration_s": 3600},
    ]

    filtered = prefilter_candidates(
        candidates=candidates,
        exclude_terms=[],
        min_duration_s=60,
        max_duration_s=1800,
    )

    ids = [c["id"] for c in filtered]
    assert ids == ["2"]
