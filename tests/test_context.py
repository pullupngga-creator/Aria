"""Unit tests for aria.context.injector (ContextInjector and TokenBudget)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from aria.context.injector import (
    ContextInjector,
    TokenBudget,
    _DEFAULT_BASE_PROMPT,
    _DEFAULT_CONTEXT_LIMIT,
    _DEFAULT_PER_DOCUMENT_CAP,
    _DEFAULT_RESERVED_FOR_RESPONSE,
)
from aria.document.tokenizer import count_tokens
from aria.document.vault import DocumentMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(
    doc_id: str,
    filename: str,
    text: str,
    *,
    storage_path: str | None = None,
) -> tuple[DocumentMetadata, Path]:
    """Create a DocumentMetadata + temp file with the given text.

    Returns (metadata, temp_path).  Caller is responsible for cleanup
    (use tmp_path fixture or tempfile context manager).
    """
    if storage_path is None:
        # Create a temp file — caller must manage its lifecycle
        fd_path = tempfile.mktemp(suffix=".txt")
        Path(fd_path).write_text(text, encoding="utf-8")
        storage_path = fd_path

    meta = DocumentMetadata(
        id=doc_id,
        filename=filename,
        original_path=f"/fake/{filename}",
        storage_path=storage_path,
        file_type=".txt",
        file_size_bytes=len(text.encode("utf-8")),
        word_count=len(text.split()),
        token_count=count_tokens(text),
        extracted_text=text,
        is_active=True,
        created_at="2026-01-01T00:00:00",
    )
    return meta, Path(storage_path)


def _mock_vault(
    documents: dict[str, DocumentMetadata],
    *,
    fail_ids: set[str] | None = None,
) -> MagicMock:
    """Build a mock VaultManager whose get_document returns the given docs."""
    vault = MagicMock()
    fail_ids = fail_ids or set()

    async def _get(doc_id: str) -> DocumentMetadata | None:
        if doc_id in fail_ids:
            raise OSError(f"Simulated read failure for {doc_id}")
        return documents.get(doc_id)

    vault.get_document = AsyncMock(side_effect=_get)
    return vault


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_texts(tmp_path: Path) -> dict[str, Path]:
    """Write several temp text files and return their paths."""
    files = {}
    samples = {
        "short.txt": "This is a short document.",
        "medium.txt": "This is a medium-length document with more content. " * 20,
        "long.txt": "This is a very long document. " * 500,
        "empty.txt": "",
    }
    for name, text in samples.items():
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        files[name] = p
    return files


@pytest.fixture
def sample_docs(tmp_texts: dict[str, Path]) -> dict[str, DocumentMetadata]:
    """Create DocumentMetadata entries backed by tmp_texts."""
    docs = {}
    for i, (name, path) in enumerate(tmp_texts.items(), start=1):
        doc_id = f"doc-{i}"
        text = path.read_text(encoding="utf-8")
        meta = DocumentMetadata(
            id=doc_id,
            filename=name,
            original_path=f"/fake/{name}",
            storage_path=str(path),
            file_type=".txt",
            file_size_bytes=path.stat().st_size,
            word_count=len(text.split()),
            token_count=count_tokens(text),
            extracted_text=text,
            is_active=True,
            created_at="2026-01-01T00:00:00",
        )
        docs[doc_id] = meta
    return docs


# ---------------------------------------------------------------------------
# Tests: TokenBudget namedtuple
# ---------------------------------------------------------------------------


class TestTokenBudget:
    """Tests for the TokenBudget NamedTuple."""

    def test_fields_exist(self) -> None:
        tb = TokenBudget(
            total_available=100,
            base_prompt_tokens=20,
            source_tokens=50,
            total_used=70,
            document_count=3,
        )
        assert tb.total_available == 100
        assert tb.base_prompt_tokens == 20
        assert tb.source_tokens == 50
        assert tb.total_used == 70
        assert tb.document_count == 3

    def test_is_tuple(self) -> None:
        tb = TokenBudget(100, 20, 50, 70, 3)
        assert isinstance(tb, tuple)
        assert len(tb) == 5

    def test_unpacking(self) -> None:
        tb = TokenBudget(100, 20, 50, 70, 3)
        avail, base, src, used, count = tb
        assert avail == 100
        assert count == 3


# ---------------------------------------------------------------------------
# Tests: No-sources path
# ---------------------------------------------------------------------------


class TestNoSources:
    """When there are no active or mentioned docs, return the base prompt."""

    @pytest.mark.asyncio
    async def test_no_active_no_mentioned(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(active_ids=set(), mentioned_ids=None)
        assert result == _DEFAULT_BASE_PROMPT

    @pytest.mark.asyncio
    async def test_empty_active_set(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(active_ids=set(), mentioned_ids=set())
        assert result == _DEFAULT_BASE_PROMPT

    @pytest.mark.asyncio
    async def test_all_docs_fail_to_read(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs, fail_ids=set(sample_docs.keys()))
        injector = ContextInjector(vault)

        result = await injector.build(active_ids=set(sample_docs.keys()))
        assert result == _DEFAULT_BASE_PROMPT

    @pytest.mark.asyncio
    async def test_empty_text_doc_skipped(
        self, sample_docs: dict
    ) -> None:
        # doc-4 is empty.txt
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(active_ids={"doc-4"})
        assert result == _DEFAULT_BASE_PROMPT


# ---------------------------------------------------------------------------
# Tests: Source injection
# ---------------------------------------------------------------------------


class TestSourceInjection:
    """Verify documents are included in the system prompt."""

    @pytest.mark.asyncio
    async def test_single_active_source(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(active_ids={"doc-1"})
        assert _DEFAULT_BASE_PROMPT in result
        assert "short.txt" in result
        assert "This is a short document." in result

    @pytest.mark.asyncio
    async def test_multiple_active_sources(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(active_ids={"doc-1", "doc-2"})
        assert "short.txt" in result
        assert "medium.txt" in result

    @pytest.mark.asyncio
    async def test_mentioned_source_included(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(
            active_ids=set(), mentioned_ids={"doc-1"}
        )
        assert "short.txt" in result

    @pytest.mark.asyncio
    async def test_source_template_format(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(active_ids={"doc-1"})
        assert "--- Document: short.txt ---" in result


# ---------------------------------------------------------------------------
# Tests: Priority ordering and deduplication
# ---------------------------------------------------------------------------


class TestPriorityAndDeduplication:
    """Active sources take priority; duplicates are included only once."""

    @pytest.mark.asyncio
    async def test_active_before_mentioned(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(
            active_ids={"doc-2"}, mentioned_ids={"doc-1"}
        )
        # Both should appear; doc-2 (active) should come before doc-1 (mentioned)
        pos_active = result.index("medium.txt")
        pos_mentioned = result.index("short.txt")
        assert pos_active < pos_mentioned

    @pytest.mark.asyncio
    async def test_deduplication(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        # doc-1 is in both active and mentioned — should appear only once
        result = await injector.build(
            active_ids={"doc-1"}, mentioned_ids={"doc-1"}
        )
        assert result.count("--- Document: short.txt ---") == 1

    @pytest.mark.asyncio
    async def test_missing_doc_id_skipped(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(
            active_ids={"doc-1", "nonexistent-id"}
        )
        assert "short.txt" in result
        # Should still succeed without the nonexistent doc


# ---------------------------------------------------------------------------
# Tests: Token budget calculation
# ---------------------------------------------------------------------------


class TestTokenBudgetCalculation:
    """Test _calculate_budget and budget-related behavior."""

    def test_default_budget(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        budget = injector._calculate_budget(user_message="", history_tokens=0)
        base_tokens = count_tokens(_DEFAULT_BASE_PROMPT)
        expected = _DEFAULT_CONTEXT_LIMIT - base_tokens - _DEFAULT_RESERVED_FOR_RESPONSE
        assert budget == expected

    def test_budget_with_user_message(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        msg = "Tell me about this document."
        budget_no_msg = injector._calculate_budget(user_message="", history_tokens=0)
        budget_with_msg = injector._calculate_budget(
            user_message=msg, history_tokens=0
        )
        msg_tokens = count_tokens(msg)
        assert budget_no_msg - budget_with_msg == msg_tokens

    def test_budget_with_history(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        budget_no_hist = injector._calculate_budget(user_message="", history_tokens=0)
        budget_with_hist = injector._calculate_budget(
            user_message="", history_tokens=500
        )
        assert budget_no_hist - budget_with_hist == 500

    def test_budget_never_negative(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault, context_limit=10)

        # With a tiny limit, overhead will exceed context_limit
        budget = injector._calculate_budget(
            user_message="some message", history_tokens=1000
        )
        assert budget == 0

    @pytest.mark.asyncio
    async def test_get_token_budget_returns_namedtuple(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        tb = await injector.get_token_budget(active_ids={"doc-1"})
        assert isinstance(tb, TokenBudget)
        assert tb.document_count == 1
        assert tb.total_available > 0


# ---------------------------------------------------------------------------
# Tests: Per-document cap and truncation
# ---------------------------------------------------------------------------


class TestCapAndTruncation:
    """Per-document cap limits individual doc tokens; truncation fits budget."""

    @pytest.mark.asyncio
    async def test_per_document_cap_limits_budget_accounting(
        self, sample_docs: dict
    ) -> None:
        """Per-document cap limits how much budget a doc consumes,
        allowing other docs to fit alongside a large doc."""
        vault = _mock_vault(sample_docs)
        # With cap=10, doc-3 (long.txt, ~3750 tokens) only consumes 10
        # tokens of budget, leaving room for doc-1 (short.txt).
        # Without the cap, doc-3 would exhaust the entire budget.
        injector = ContextInjector(
            vault,
            context_limit=500,
            reserved_for_response=10,
            per_document_cap=10,
        )

        result = await injector.build(active_ids={"doc-3", "doc-1"})
        # Both docs should appear — cap on doc-3 leaves room for doc-1
        assert "long.txt" in result
        assert "short.txt" in result

    @pytest.mark.asyncio
    async def test_truncation_when_budget_exhausted(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        # Use a tiny context limit so budget is very small
        injector = ContextInjector(
            vault,
            context_limit=100,
            reserved_for_response=10,
        )

        result = await injector.build(active_ids={"doc-3"})
        # Should either truncate or drop the long doc
        assert "truncated" in result or result == _DEFAULT_BASE_PROMPT

    @pytest.mark.asyncio
    async def test_zero_budget_returns_base_prompt(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(
            vault,
            context_limit=10,  # effectively zero budget
            reserved_for_response=10,
        )

        result = await injector.build(active_ids={"doc-1"})
        # Budget will be 0, so no sources can fit
        assert result == _DEFAULT_BASE_PROMPT


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify graceful handling of read failures."""

    @pytest.mark.asyncio
    async def test_oserror_on_read(self, sample_docs: dict) -> None:
        vault = _mock_vault(sample_docs, fail_ids={"doc-1"})
        injector = ContextInjector(vault)

        # Should not raise, just skip the doc
        result = await injector.build(active_ids={"doc-1"})
        assert result == _DEFAULT_BASE_PROMPT

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs, fail_ids={"doc-1"})
        injector = ContextInjector(vault)

        # doc-1 fails, doc-2 succeeds
        result = await injector.build(active_ids={"doc-1", "doc-2"})
        # doc-2 (medium.txt) should still be in the prompt
        assert "medium.txt" in result

    @pytest.mark.asyncio
    async def test_get_document_returns_none(
        self, sample_docs: dict
    ) -> None:
        # Remove doc-1 from the vault lookup
        del sample_docs["doc-1"]
        vault = _mock_vault(sample_docs)
        injector = ContextInjector(vault)

        result = await injector.build(active_ids={"doc-1"})
        assert result == _DEFAULT_BASE_PROMPT


# ---------------------------------------------------------------------------
# Tests: Custom base prompt
# ---------------------------------------------------------------------------


class TestCustomBasePrompt:
    """Verify custom base prompt overrides the default."""

    @pytest.mark.asyncio
    async def test_custom_base_prompt_no_sources(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        custom = "You are a specialized assistant."
        injector = ContextInjector(vault, base_prompt=custom)

        result = await injector.build(active_ids=set())
        assert result == custom

    @pytest.mark.asyncio
    async def test_custom_base_prompt_with_sources(
        self, sample_docs: dict
    ) -> None:
        vault = _mock_vault(sample_docs)
        custom = "You are a specialized assistant."
        injector = ContextInjector(vault, base_prompt=custom)

        result = await injector.build(active_ids={"doc-1"})
        assert custom in result
        assert "short.txt" in result
