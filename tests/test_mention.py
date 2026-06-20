"""Tests for aria.context.mention — @-mention parser and fuzzy search."""

import pytest

from aria.context.mention import (
    MentionMatch,
    detect_active_trigger,
    find_mentions,
    fuzzy_score,
    search_documents,
)


# ---------------------------------------------------------------------------
# find_mentions
# ---------------------------------------------------------------------------


class TestFindMentions:
    """Tests for find_mentions()."""

    def test_simple(self) -> None:
        """Single @file.pdf in text."""
        text = "Tell me about @report.pdf please"
        matches = find_mentions(text)
        assert len(matches) == 1
        assert matches[0].query == "report.pdf"
        assert matches[0].start == text.index("@")
        assert matches[0].end == text.index("report.pdf") + len("report.pdf")

    def test_multiple(self) -> None:
        """Multiple @mentions in one message."""
        text = "Compare @doc1.pdf and @doc2.txt for me"
        matches = find_mentions(text)
        assert len(matches) == 2
        assert matches[0].query == "doc1.pdf"
        assert matches[1].query == "doc2.txt"

    def test_no_match(self) -> None:
        """Plain text with no @ symbols."""
        text = "This is a normal message with no mentions"
        assert find_mentions(text) == []

    def test_at_end_with_query(self) -> None:
        """@query at the very end of text (still a valid completed mention)."""
        text = "ask @helper"
        matches = find_mentions(text)
        assert len(matches) == 1
        assert matches[0].query == "helper"

    def test_lone_at_sign(self) -> None:
        """A lone @ at end of text is not a completed mention (regex requires ≥1 char)."""
        text = "type @"
        # The regex requires at least one word char, so bare @ won't match.
        matches = find_mentions(text)
        assert matches == []

    def test_at_start_of_message(self) -> None:
        """@mention at the very start of a message."""
        text = "@first.pdf what does this say?"
        matches = find_mentions(text)
        assert len(matches) == 1
        assert matches[0].query == "first.pdf"
        assert matches[0].start == 0

    def test_hyphenated_filename(self) -> None:
        """@mention with hyphens in filename."""
        text = "Check @my-report.pdf"
        matches = find_mentions(text)
        assert len(matches) == 1
        assert matches[0].query == "my-report.pdf"

    def test_empty_text(self) -> None:
        """Empty input returns no matches."""
        assert find_mentions("") == []


# ---------------------------------------------------------------------------
# detect_active_trigger
# ---------------------------------------------------------------------------


class TestDetectActiveTrigger:
    """Tests for detect_active_trigger()."""

    def test_active_at_end(self) -> None:
        """Cursor at end of text with active @-mention."""
        assert detect_active_trigger("hello @res") == "res"

    def test_active_just_at_sign(self) -> None:
        """Just typed @, query is empty string."""
        assert detect_active_trigger("hello @") == ""

    def test_none_after_space(self) -> None:
        """Space terminates the trigger — no longer active."""
        assert detect_active_trigger("hello @res ") is None

    def test_none_plain_text(self) -> None:
        """Plain text with no @ symbol."""
        assert detect_active_trigger("hello world") is None

    def test_none_empty(self) -> None:
        """Empty input returns None."""
        assert detect_active_trigger("") is None

    def test_active_with_explicit_cursor(self) -> None:
        """Cursor inside an active @-mention at an explicit position."""
        # cursor at position 9 (inside "@query")
        # text:  "ask @qu|ery"  cursor_pos=8
        text = "ask @query"
        # cursor_pos=8 means cursor is after "ask @que" → query = "que"
        result = detect_active_trigger(text, cursor_pos=8)
        assert result == "que"

    def test_none_cursor_after_space(self) -> None:
        """Cursor is after a space — trigger has ended."""
        # "ask @file " with cursor at end (pos=10)
        assert detect_active_trigger("ask @file ", cursor_pos=10) is None

    def test_none_completed_mention_then_more_text(self) -> None:
        """A completed mention followed by more text is not active."""
        # "@file.pdf more text" — cursor at end
        assert detect_active_trigger("@file.pdf more text") is None

    def test_active_mid_text_with_cursor(self) -> None:
        """Cursor inside @-mention in the middle of text."""
        text = "ask @ab then more"
        # Place cursor at position 7 (just after "@ab")
        result = detect_active_trigger(text, cursor_pos=7)
        assert result == "ab"

    def test_none_only_non_at_special_chars(self) -> None:
        """Typing special chars after space — no active trigger."""
        assert detect_active_trigger("hello @foo bar!") is None


# ---------------------------------------------------------------------------
# fuzzy_score
# ---------------------------------------------------------------------------


class TestFuzzyScore:
    """Tests for fuzzy_score()."""

    def test_exact_match_case_insensitive(self) -> None:
        """Exact match (case-insensitive) scores 100."""
        score = fuzzy_score("report.pdf", "Report.PDF")
        assert score == 100.0

    def test_exact_match_case_exact(self) -> None:
        """Exact match with identical casing gets +10 bonus."""
        score = fuzzy_score("report.pdf", "report.pdf")
        assert score == 110.0

    def test_prefix_match(self) -> None:
        """Prefix match scores 80."""
        score = fuzzy_score("rep", "report.pdf")
        assert score == 80.0

    def test_prefix_no_bonus_for_case_mismatch(self) -> None:
        """Prefix match where query != target does not get the exact-casing bonus."""
        # "Rep" != "Report.pdf" so no bonus; prefix tier = 80
        score = fuzzy_score("Rep", "Report.pdf")
        assert score == 80.0

    def test_prefix_case_exact_bonus(self) -> None:
        """Exact match (query == target) with identical casing scores 110."""
        # query == target → exact tier (100) + case-exact bonus (10)
        score = fuzzy_score("report.pdf", "report.pdf")
        assert score == 110.0

    def test_substring_match(self) -> None:
        """Substring match (not prefix) scores 60."""
        score = fuzzy_score("port", "report.pdf")
        assert score == 60.0

    def test_subsequence_match(self) -> None:
        """Subsequence match (chars in order but not contiguous) scores 30."""
        # "rpt" → r...p...t in "report.txt"
        score = fuzzy_score("rpt", "report.txt")
        assert score == 30.0

    def test_no_match(self) -> None:
        """Completely unrelated strings score 0."""
        assert fuzzy_score("xyz", "report.pdf") == 0.0

    def test_empty_query(self) -> None:
        """Empty query matches everything with baseline score."""
        score = fuzzy_score("", "anything.pdf")
        assert score == 50.0

    def test_empty_target(self) -> None:
        """Non-empty query against empty target scores 0."""
        assert fuzzy_score("hello", "") == 0.0

    def test_both_empty(self) -> None:
        """Both empty returns baseline."""
        assert fuzzy_score("", "") == 50.0

    def test_case_insensitive_substring(self) -> None:
        """Substring match is case-insensitive."""
        score = fuzzy_score("PDF", "report.pdf")
        # "pdf" is in "report.pdf" → substring tier = 60
        assert score == 60.0


# ---------------------------------------------------------------------------
# search_documents
# ---------------------------------------------------------------------------


class TestSearchDocuments:
    """Tests for search_documents()."""

    @pytest.fixture
    def sample_docs(self) -> list[dict]:
        """A small list of vault document dicts for testing."""
        return [
            {"id": "1", "filename": "report.pdf", "extracted_text": "annual report"},
            {"id": "2", "filename": "notes.txt", "extracted_text": "meeting notes"},
            {"id": "3", "filename": "research-paper.pdf", "extracted_text": "study results"},
            {"id": "4", "filename": "data.csv", "extracted_text": "raw data"},
        ]

    def test_sorted_results(self, sample_docs: list[dict]) -> None:
        """Results are sorted by score, best first."""
        results = search_documents("rep", sample_docs)
        # "report.pdf" has prefix match (80), "research-paper.pdf" has substring (60)
        assert len(results) >= 2
        filenames = [d["filename"] for d in results]
        assert filenames[0] == "report.pdf"
        # "research-paper.pdf" also contains "rep" as substring
        assert "research-paper.pdf" in filenames

    def test_empty_query_returns_all(self, sample_docs: list[dict]) -> None:
        """Empty query returns all documents (score=50 for all)."""
        results = search_documents("", sample_docs)
        assert len(results) == len(sample_docs)

    def test_no_results(self, sample_docs: list[dict]) -> None:
        """Query with no matches returns empty list."""
        results = search_documents("zzzzz", sample_docs)
        assert results == []

    def test_exact_match_first(self, sample_docs: list[dict]) -> None:
        """Exact filename match comes first."""
        results = search_documents("notes.txt", sample_docs)
        assert len(results) >= 1
        assert results[0]["filename"] == "notes.txt"

    def test_empty_documents_list(self) -> None:
        """Empty document list returns empty results."""
        assert search_documents("anything", []) == []

    def test_preserves_document_references(self, sample_docs: list[dict]) -> None:
        """Returned dicts are the same objects (not copies)."""
        results = search_documents("report", sample_docs)
        assert results[0] is sample_docs[0]

    def test_subsequence_match_included(self, sample_docs: list[dict]) -> None:
        """Subsequence matches are included (lowest tier)."""
        # "rdt" is a subsequence of "report.txt"? r...d...t? No.
        # "rd" is a subsequence of "report.pdf" → r...d in "report.pdf"? r-e-p-o-r-t-.-p-d-f → "r" at 0, "d" at 8? "pdf" has "d" at position 9 → yes
        # Actually let's use "rpt" which is clearly a subsequence of "report.pdf"
        results = search_documents("rpt", sample_docs)
        filenames = [d["filename"] for d in results]
        assert "report.pdf" in filenames
