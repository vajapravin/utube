"""Career focus and anti-entertainment guardrail filters (FR-AntiDoom)."""

import re
from typing import Any, Dict, List, Set

ANTI_ENTERTAINMENT_KEYWORDS: Set[str] = {
    "prank",
    "pranks",
    "funny",
    "comedy",
    "comedian",
    "meme",
    "memes",
    "tiktok",
    "reaction",
    "reacts",
    "vlog",
    "daily vlog",
    "drama",
    "gossip",
    "celebrity",
    "parody",
    "skit",
    "entertainment",
    "gaming",
    "gameplay",
    "playthrough",
    "fails",
    "fail compilation",
    "challenge",
    "try not to laugh",
    "unboxing",
    "humor",
    "joke",
    "jokes",
    "shorts trap",
    "asmr",
    "slime",
    "toy",
    "toys",
    "cartoon",
    "cartoons",
    "minecraft",
    "roblox",
    "fortnite",
    "beauty",
    "makeup",
    "skincare",
    "fashion haul",
    "shopping haul",
    "outfit",
    "dance",
    "dances",
    "trolling",
    "viral video",
}

CLICKBAIT_REGEX = re.compile(
    r"\b(shocking|you won't believe|gone wrong|insane|mind blown|what happened next|don't do this|secret trick)\b",
    re.IGNORECASE,
)

CAREER_LEARNING_KEYWORDS: Set[str] = {
    "tutorial",
    "tutorials",
    "guide",
    "course",
    "full course",
    "deep dive",
    "system design",
    "architecture",
    "explained",
    "masterclass",
    "best practices",
    "fundamentals",
    "overview",
    "crash course",
    "interview",
    "hands on",
    "walkthrough",
    "production",
    "roadmap",
    "engineering",
    "development",
    "machine learning",
    "artificial intelligence",
    "neural network",
    "transformers",
    "backend",
    "frontend",
    "devops",
}

STOP_WORDS: Set[str] = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "was", "what", "when", "where", "who", "will", "with", "want",
    "need", "give", "show", "videos", "video", "content", "channel",
    "recommend", "shorts", "per", "below", "structure", "following",
    "topics", "topic", "list", "curate", "find", "make", "please",
    "introduction", "intro", "basics", "learn", "learning", "guide",
}



def is_entertainment_or_clickbait(title: str, description: str = "") -> bool:
    """Check if a video falls into entertainment, comedy, prank, or sensationalist clickbait."""
    lower_title = title.lower()
    lower_desc = description.lower()[:300]
    combined = f"{lower_title} {lower_desc}"

    # 1. Check anti-entertainment keyword matches in title
    title_words = set(re.findall(r"\b\w+\b", lower_title))
    if title_words & ANTI_ENTERTAINMENT_KEYWORDS:
        return True

    # 2. Check clickbait regex patterns
    if CLICKBAIT_REGEX.search(lower_title):
        return True

    # 3. Check for excessive exclamation or question marks
    if title.count("!") >= 3 or title.count("?") >= 3:
        return True

    # 4. Check all-caps shouting titles (e.g., "OMG HE REALLY DID THIS")
    letters = [c for c in title if c.isalpha()]
    if len(letters) > 15:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio > 0.65:
            # Check if it has tech acronyms vs shouting
            tech_acronyms = {"API", "AWS", "GCP", "CSS", "HTML", "SQL", "REST", "JSON", "HTTP", "CI", "CD", "LLM", "AI"}
            words_in_title = title.split()
            shouting_words = [w for w in words_in_title if w.isupper() and len(w) > 3 and w not in tech_acronyms]
            if len(shouting_words) >= 3:
                return True

    return False


def build_career_focused_queries(prompt: str) -> List[str]:
    """Decompose user prompt into high-precision technical queries with syllabus extraction."""
    # 1. Check for numbered or bulleted syllabus items
    syllabus_lines = re.findall(
        r"(?:^\s*\d+[\.\)]\s*|^\s*[-*•]\s*)(.+)$", prompt.strip(), re.MULTILINE
    )
    extracted_queries: List[str] = []

    if syllabus_lines:
        for line in syllabus_lines:
            clean_line = re.sub(r"[^\w\s-]", " ", line).strip()
            tokens = [w for w in clean_line.split() if w.lower() not in STOP_WORDS and len(w) > 2]
            if tokens:
                extracted_queries.append(" ".join(tokens[:5]))

    if extracted_queries:
        # Return top 4 distinct topics formatted as engineering tutorials
        formatted = []
        for q in extracted_queries[:4]:
            formatted.append(f"{q} tutorial")
        if len(formatted) < 4:
            formatted.append(f"{extracted_queries[0]} full course")
        return formatted

    # 2. Freeform text prompt fallback
    clean = re.sub(r"[^\w\s-]", " ", prompt.strip())
    words = [w for w in clean.split() if len(w) > 2 and w.lower() not in STOP_WORDS]

    if not words:
        words = ["software", "engineering"]

    subject = " ".join(words[:4])
    return [
        f"{subject} tutorial",
        f"{subject} full course",
        f"{subject} architecture deep dive",
        f"{subject} best practices explained",
    ]


def evaluate_career_relevance(prompt: str, candidate: Dict[str, Any]) -> int:
    """Score candidate video from 0 to 100 based on career learning relevance.

    Returns:
        int: Score between 0 and 100. >= 60 represents career relevance.
    """
    title = candidate.get("title", "")
    desc = candidate.get("description", "")
    duration_s = candidate.get("duration_s", 0)

    # 1. Instant drop for entertainment/clickbait/pranks
    if is_entertainment_or_clickbait(title, desc):
        return 0

    # 2. Extract meaningful keywords from prompt
    clean_prompt = re.sub(r"[^\w\s]", " ", prompt.lower())
    prompt_tokens = set(w for w in clean_prompt.split() if len(w) > 2 and w not in STOP_WORDS)

    clean_title = re.sub(r"[^\w\s]", " ", title.lower())
    title_tokens = set(clean_title.split())

    clean_desc = re.sub(r"[^\w\s]", " ", desc.lower())
    desc_tokens = set(clean_desc.split())

    overlap_title = len(prompt_tokens & title_tokens)
    overlap_desc = len(prompt_tokens & desc_tokens)

    # If the video does NOT match any prompt tokens, reject it (0 relevance)
    if overlap_title == 0 and overlap_desc == 0:
        return 0

    # Base score for genuine prompt match
    score = 60

    # Reward title keyword overlap
    score += min(25, overlap_title * 10)

    # Reward description overlap
    if overlap_desc > 0:
        score += min(10, overlap_desc * 2)

    # Reward educational keywords in title
    if title_tokens & CAREER_LEARNING_KEYWORDS:
        score += 10

    # Slight reward for deep dives
    if duration_s >= 600:
        score += 5

    return max(0, min(100, score))


