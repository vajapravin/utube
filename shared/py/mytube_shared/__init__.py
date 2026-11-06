"""mytube shared package."""

from mytube_shared.guardrails import (
    ANTI_ENTERTAINMENT_KEYWORDS,
    CAREER_LEARNING_KEYWORDS,
    build_career_focused_queries,
    evaluate_career_relevance,
    is_entertainment_or_clickbait,
)
from mytube_shared.prefilter import prefilter_candidates

__version__ = "0.1.0"
__all__ = [
    "ANTI_ENTERTAINMENT_KEYWORDS",
    "CAREER_LEARNING_KEYWORDS",
    "build_career_focused_queries",
    "evaluate_career_relevance",
    "is_entertainment_or_clickbait",
    "prefilter_candidates",
]
