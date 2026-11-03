"""Lexorank string utilities for O(1) item reordering."""


def get_initial_rank(step: int = 1000) -> str:
    """Return an initial rank string for the first item."""
    return f"{step:06d}"


def get_rank_between(prev_rank: str | None, next_rank: str | None) -> str:
    """Generate a lexicographically ordered string strictly between prev_rank and next_rank.

    Supports insertion at beginning, middle, and end.
    """
    if prev_rank is None and next_rank is None:
        return "001000"
    if prev_rank is None:
        # Insert before next_rank: prepend '0' or halve the value
        return "0" + next_rank
    if next_rank is None:
        # Append after prev_rank
        # If numeric, increment
        try:
            val = int(prev_rank)
            return f"{val + 1000:06d}"
        except ValueError:
            return prev_rank + "m"

    # Between prev_rank and next_rank
    # Find common prefix and generate midpoint
    p = prev_rank
    n = next_rank
    max_len = max(len(p), len(n))
    p = p.ljust(max_len + 1, "0")
    n = n.ljust(max_len + 1, "0")

    # Find first differing index
    diff_idx = 0
    while diff_idx < len(p) and p[diff_idx] == n[diff_idx]:
        diff_idx += 1

    if diff_idx < len(p):
        p_char = ord(p[diff_idx])
        n_char = ord(n[diff_idx])
        if n_char - p_char > 1:
            mid_char = chr((p_char + n_char) // 2)
            return p[:diff_idx] + mid_char
        else:
            return p[: diff_idx + 1] + "m"
    return prev_rank + "m"
