"""@-mention parser and fuzzy search for vault documents.

Pure-logic module with no Flet dependency. Used by InputBar to detect
active @-mention triggers and by ChatPanel to filter/sort vault documents.
"""

import re
from typing import NamedTuple

# Matches @filename where filename is word chars, hyphens, or dots.
_MENTION_RE = re.compile(r"@([\w\-.]+)")


class MentionMatch(NamedTuple):
    """A single @-mention match found in input text."""

    query: str  # text after @, without the @
    start: int  # start index of @ in the full text
    end: int  # end index (exclusive) of the query


# ---------------------------------------------------------------------------
# Mention extraction
# ---------------------------------------------------------------------------


def find_mentions(text: str) -> list[MentionMatch]:
    """Return all completed @mention matches with positions.

    A "completed" mention is one where the @ is followed by at least one
    non-whitespace character.  The returned positions cover the full span
    from @ to the end of the query token.

    Args:
        text: Raw input text from the message field.

    Returns:
        List of MentionMatch tuples, in order of appearance.
    """
    return [
        MentionMatch(query=m.group(1), start=m.start(), end=m.end())
        for m in _MENTION_RE.finditer(text)
    ]


def detect_active_trigger(text: str, cursor_pos: int | None = None) -> str | None:
    """Detect whether the cursor is inside an active (in-progress) @mention.

    An "active trigger" is the rightmost `@` followed by zero or more
    non-whitespace characters that extends to the cursor position (or end
    of text when cursor_pos is unavailable).

    Examples::

        "hello @res"          -> "res"   (active at end of text)
        "hello @res "         -> None    (space terminates the trigger)
        "@file.pdf more text" -> None    (completed mention, not active)
        "ask @doc about X"    -> None    (cursor assumed at end; "X" ≠ @-token)
        "ask @ab"             -> "ab"    (active trigger)
        "@"                   -> ""      (just typed @, empty query)

    Args:
        text: Current input text.
        cursor_pos: Optional 0-based cursor index.  When None, the end of
            the text is assumed.

    Returns:
        The query string (without the @) if an active trigger is found,
        or None if the cursor is not inside a mention.
    """
    if not text:
        return None

    pos = cursor_pos if cursor_pos is not None else len(text)

    # Walk backwards from cursor to find the nearest @ that starts the token.
    # We stop if we hit whitespace (meaning the @ token ended before cursor).
    i = pos - 1
    while i >= 0:
        ch = text[i]
        if ch == "@":
            # Found @ — extract the query from just after @ to cursor
            query = text[i + 1 : pos]
            # The query must contain no whitespace (otherwise the trigger ended)
            if " " in query or "\t" in query or "\n" in query:
                return None
            return query
        if ch in (" ", "\t", "\n"):
            # Hit whitespace before @, so we're not inside a mention
            return None
        i -= 1

    return None


# ---------------------------------------------------------------------------
# Fuzzy scoring
# ---------------------------------------------------------------------------


def _is_subsequence(query: str, target: str) -> bool:
    """Return True if query is a subsequence of target (case-insensitive)."""
    q, t = query.lower(), target.lower()
    qi = 0
    for ch in t:
        if qi < len(q) and ch == q[qi]:
            qi += 1
    return qi == len(q)


def fuzzy_score(query: str, target: str) -> float:
    """Score how well *query* matches *target* (a filename or content preview).

    Returns a float >= 0.  Higher is better.  0 means no match.

    Scoring tiers:
    - Exact match (case-insensitive): 100
    - Starts with query:             80
    - Contains query as substring:   60
    - Subsequence match:             30
    - No match:                       0

    Bonus: +10 when the comparison is case-exact (preserves original casing).

    Args:
        query: The search string typed by the user (without @).
        target: The candidate string to score against.

    Returns:
        Numeric score; 0 means no match.
    """
    if not query:
        # Empty query matches everything equally; return baseline.
        return 50.0

    if not target:
        return 0.0

    q_lower = query.lower()
    t_lower = target.lower()

    if q_lower == t_lower:
        score = 100.0
    elif t_lower.startswith(q_lower):
        score = 80.0
    elif q_lower in t_lower:
        score = 60.0
    elif _is_subsequence(q_lower, t_lower):
        score = 30.0
    else:
        return 0.0

    # Bonus for exact casing match
    if query == target:
        score += 10.0

    return score


def search_documents(
    query: str,
    documents: list[dict],
    *,
    min_score: float = 1.0,
) -> list[dict]:
    """Fuzzy-search documents by filename, returning matches sorted best-first.

    Each document dict is expected to have at least a ``"filename"`` key.
    Documents scoring below *min_score* are excluded.

    Args:
        query: Search string (without the leading @).
        documents: List of document dicts from app_state.
        min_score: Minimum score threshold (default 1.0 — any match).

    Returns:
        Filtered and sorted list of document dicts (same references, not copies).
    """
    scored: list[tuple[float, dict]] = []
    for doc in documents:
        filename = doc.get("filename", "")
        score = fuzzy_score(query, filename)
        if score >= min_score:
            scored.append((score, doc))

    # Sort descending by score
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _score, doc in scored]
