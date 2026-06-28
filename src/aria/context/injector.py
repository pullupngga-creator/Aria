"""System prompt builder with token-budgeted source injection.

Assembles context-aware system prompts by reading active and @-mentioned
source documents, fitting them into a configurable token budget with
priority-based assembly (active sources > mentioned sources).
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, NamedTuple

from aria.document.tokenizer import count_tokens
from aria.document.vault import VaultManager
from aria.exceptions import ContextError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default base system prompt (used when no custom prompt is provided)
_DEFAULT_BASE_PROMPT: str = (
    "You are Aria, a knowledgeable research assistant. "
    "You help users analyze documents, answer questions, and think critically. "
    "Be concise, accurate, and cite sources when referencing provided documents."
)

# Module-level defaults (overridable via Settings)
_DEFAULT_CONTEXT_LIMIT: int = 128_000
_DEFAULT_RESERVED_FOR_RESPONSE: int = 8_192
_DEFAULT_PER_DOCUMENT_CAP: int = 16_000

# Approximate chars-per-token ratio for character-based truncation fallback.
_CHARS_PER_TOKEN: int = 4

# Prompt templates
_SYSTEM_PROMPT_TEMPLATE: str = (
    "{base_prompt}\n\n"
    "The following documents have been provided as context. "
    "Use them to inform your responses. "
    "When referencing information from these documents, cite the source filename.\n\n"
    "{sources_block}"
)

_SOURCE_TEMPLATE: str = "--- Document: {filename} ---\n{text}"


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class TokenBudget(NamedTuple):
    """Breakdown of token allocation for a single prompt assembly."""

    total_available: int  # tokens available for source documents
    base_prompt_tokens: int  # tokens used by the base system prompt
    source_tokens: int  # tokens used by injected source text
    total_used: int  # base + sources (excl. user message & history)
    document_count: int  # number of documents actually injected


class TokenUsage(NamedTuple):
    """Full token allocation breakdown for UI display.

    Provides a comprehensive view of how the context window budget
    is allocated across all components.
    """

    base_prompt_tokens: int  # tokens used by the base system prompt
    source_tokens: int  # tokens used by injected sources (after cap/truncation)
    user_message_tokens: int  # tokens in the current user message
    history_tokens: int  # tokens in conversation history
    reserved_tokens: int  # tokens reserved for model response
    total_used: int  # sum of all above
    context_limit: int  # maximum tokens allowed
    remaining: int  # context_limit - total_used (can be negative if exceeded)
    utilization: float  # total_used / context_limit (0.0–1.0+; >1.0 = exceeded)
    document_count: int  # number of source documents included


# ---------------------------------------------------------------------------
# ContextInjector
# ---------------------------------------------------------------------------


class ContextInjector:
    """Assembles system prompts with source document context injection.

    The injector reads document text from the vault, counts tokens, and
    fits sources into a configurable budget.  Active (globally toggled)
    sources have priority over @-mentioned sources.

    This is a pure service class — no Flet dependency, no UI state.
    """

    def __init__(
        self,
        vault_manager: VaultManager,
        *,
        base_prompt: str = _DEFAULT_BASE_PROMPT,
        context_limit: int = _DEFAULT_CONTEXT_LIMIT,
        reserved_for_response: int = _DEFAULT_RESERVED_FOR_RESPONSE,
        per_document_cap: int = _DEFAULT_PER_DOCUMENT_CAP,
    ) -> None:
        """Initialize the context injector.

        Args:
            vault_manager: VaultManager instance for reading document metadata.
            base_prompt: The base system prompt text (constant prefix).
            context_limit: Total token budget for the context window.
            reserved_for_response: Tokens reserved for the model's reply.
            per_document_cap: Maximum tokens any single source document may use.
        """
        self._vault_manager = vault_manager
        self._base_prompt = base_prompt
        self._context_limit = context_limit
        self._reserved_for_response = reserved_for_response
        self._per_document_cap = per_document_cap

    # ── Public API ──────────────────────────────────────────────────────────────

    async def calculate_usage(
        self,
        active_ids: set[str],
        mentioned_ids: set[str] | None = None,
        *,
        user_message: str = "",
        history_tokens: int = 0,
    ) -> TokenUsage:
        """Calculate the full token usage breakdown without building the prompt.

        Reads sources, caps per-document, and sums all budget categories.
        This is a lightweight read-only calculation suitable for UI display.

        Args:
            active_ids: IDs of globally activated documents.
            mentioned_ids: IDs of @-mentioned documents.
            user_message: The current user message text.
            history_tokens: Token count of conversation history.

        Returns:
            TokenUsage namedtuple with the full allocation breakdown.
        """
        base_tokens = count_tokens(self._base_prompt)
        user_tokens = count_tokens(user_message) if user_message else 0

        # Read sources and sum their tokens (capped per-document)
        ordered_ids = self._merge_ids(active_ids, mentioned_ids)
        total_source_tokens = 0
        doc_count = 0
        for doc_id in ordered_ids:
            result = await self._read_source_text(doc_id)
            if result is not None:
                capped = min(result[2], self._per_document_cap)
                total_source_tokens += capped
                doc_count += 1

        # Available budget for sources
        budget = self._calculate_budget(user_message, history_tokens)
        # Actual source tokens used is min of total and budget
        actual_source = min(total_source_tokens, budget)

        total_used = (
            base_tokens + actual_source + user_tokens + history_tokens
            + self._reserved_for_response
        )
        remaining = self._context_limit - total_used
        utilization = total_used / self._context_limit if self._context_limit > 0 else 0.0

        return TokenUsage(
            base_prompt_tokens=base_tokens,
            source_tokens=actual_source,
            user_message_tokens=user_tokens,
            history_tokens=history_tokens,
            reserved_tokens=self._reserved_for_response,
            total_used=total_used,
            context_limit=self._context_limit,
            remaining=remaining,
            utilization=utilization,
            document_count=doc_count,
        )

    @staticmethod
    def count_history_tokens(messages: list[dict[str, Any]]) -> int:
        """Sum token counts for all messages in conversation history.

        Args:
            messages: List of message dicts with 'content' keys.

        Returns:
            Total token count across all messages.
        """
        return sum(count_tokens(m.get("content", "")) for m in messages)

    async def build(
        self,
        active_ids: set[str],
        mentioned_ids: set[str] | None = None,
        *,
        user_message: str = "",
        history_tokens: int = 0,
    ) -> str:
        """Build a system prompt with source documents injected.

        Priority order (highest first):
        1. Active sources (globally toggled documents)
        2. @-mentioned sources (per-message context)

        Sources are deduplicated (a doc in both sets is included once, at
        active priority).  When the token budget is exhausted, remaining
        lower-priority sources are truncated or dropped.

        Args:
            active_ids: IDs of globally activated documents.
            mentioned_ids: IDs of @-mentioned documents from the current input.
            user_message: The current user message (counted toward budget).
            history_tokens: Approximate token count of conversation history.

        Returns:
            Complete system prompt string ready for the LLM.
        """
        # 1. Merge and deduplicate, preserving priority order
        ordered_ids = self._merge_ids(active_ids, mentioned_ids)

        if not ordered_ids:
            return self._base_prompt

        # 2. Read all source texts
        sources: list[tuple[str, str, int]] = []  # (filename, text, tokens)
        for doc_id in ordered_ids:
            result = await self._read_source_text(doc_id)
            if result is not None:
                sources.append(result)

        if not sources:
            return self._base_prompt

        # 3. Calculate available budget
        budget = self._calculate_budget(user_message, history_tokens)

        # 4. Fit sources into budget
        fitted_sources, total_source_tokens = self._assemble_sources(sources, budget)

        if not fitted_sources:
            return self._base_prompt

        # 5. Assemble final prompt
        sources_block = "\n\n".join(
            _SOURCE_TEMPLATE.format(filename=fn, text=text)
            for fn, text in fitted_sources
        )

        return _SYSTEM_PROMPT_TEMPLATE.format(
            base_prompt=self._base_prompt,
            sources_block=sources_block,
        )

    async def get_token_budget(
        self,
        active_ids: set[str],
        mentioned_ids: set[str] | None = None,
        *,
        user_message: str = "",
        history_tokens: int = 0,
    ) -> TokenBudget:
        """Calculate the token budget breakdown without building the full prompt.

        Useful for displaying context window usage in the UI.

        Args:
            active_ids: IDs of globally activated documents.
            mentioned_ids: IDs of @-mentioned documents.
            user_message: The current user message.
            history_tokens: Approximate token count of conversation history.

        Returns:
            TokenBudget namedtuple with the allocation breakdown.
        """
        ordered_ids = self._merge_ids(active_ids, mentioned_ids)

        # Read sources and sum their tokens
        total_source_tokens = 0
        doc_count = 0
        for doc_id in ordered_ids:
            result = await self._read_source_text(doc_id)
            if result is not None:
                # Cap per-document
                capped = min(result[2], self._per_document_cap)
                total_source_tokens += capped
                doc_count += 1

        budget = self._calculate_budget(user_message, history_tokens)
        base_tokens = count_tokens(self._base_prompt)

        # Actual source tokens used is min of total and budget
        actual_source = min(total_source_tokens, budget)

        return TokenBudget(
            total_available=budget,
            base_prompt_tokens=base_tokens,
            source_tokens=actual_source,
            total_used=base_tokens + actual_source,
            document_count=doc_count,
        )

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _merge_ids(
        self,
        active_ids: set[str],
        mentioned_ids: set[str] | None,
    ) -> list[str]:
        """Merge active and mentioned IDs, deduplicating with priority order.

        Active IDs come first (higher priority), then mentioned IDs that
        aren't already in the active set.
        """
        seen: set[str] = set()
        ordered: list[str] = []

        for doc_id in active_ids:
            if doc_id not in seen:
                seen.add(doc_id)
                ordered.append(doc_id)

        if mentioned_ids:
            for doc_id in mentioned_ids:
                if doc_id not in seen:
                    seen.add(doc_id)
                    ordered.append(doc_id)

        return ordered

    async def _read_source_text(
        self, doc_id: str
    ) -> tuple[str, str, int] | None:
        """Read a document's extracted text and count its tokens.

        Returns:
            (filename, text, token_count) or None if not found / unreadable.
        """
        try:
            doc = await self._vault_manager.get_document(doc_id)
            if doc is None:
                logger.warning("Document %s not found in vault, skipping", doc_id)
                return None

            storage_path = Path(doc.storage_path)
            text = await asyncio.to_thread(storage_path.read_text, encoding="utf-8")

            if not text.strip():
                logger.info("Document %s has empty text, skipping", doc_id)
                return None

            token_count = count_tokens(text)
            return (doc.filename, text, token_count)

        except (OSError, UnicodeDecodeError) as e:
            logger.warning(
                "Failed to read source document %s: %s", doc_id, e
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error reading document %s: %s", doc_id, e,
                exc_info=True,
            )
            return None

    def _calculate_budget(
        self,
        user_message: str,
        history_tokens: int,
    ) -> int:
        """Calculate available tokens for source documents.

        budget = context_limit - base_prompt - user_message - history - reserved
        """
        base_tokens = count_tokens(self._base_prompt)
        user_tokens = count_tokens(user_message) if user_message else 0
        overhead = base_tokens + user_tokens + history_tokens + self._reserved_for_response
        return max(0, self._context_limit - overhead)

    def _assemble_sources(
        self,
        sources: list[tuple[str, str, int]],
        budget: int,
    ) -> tuple[list[tuple[str, str]], int]:
        """Fit sources into the token budget, truncating or dropping as needed.

        Iterates through sources in priority order.  Each source is capped
        at per_document_cap tokens.  When the budget runs low, the current
        source is truncated to fit; subsequent sources are dropped.

        Args:
            sources: List of (filename, text, token_count) tuples, in
                priority order.
            budget: Maximum tokens available for all sources combined.

        Returns:
            (fitted_sources, total_tokens_used) where fitted_sources is a
            list of (filename, possibly_truncated_text).
        """
        fitted: list[tuple[str, str]] = []
        remaining = budget

        for filename, text, token_count in sources:
            if remaining <= 0:
                break

            # Cap individual document
            effective_tokens = min(token_count, self._per_document_cap)

            if effective_tokens <= remaining:
                # Source fits entirely
                fitted.append((filename, text))
                remaining -= effective_tokens
            else:
                # Source exceeds remaining budget — truncate
                # Use character approximation: remaining_tokens * chars_per_token
                max_chars = remaining * _CHARS_PER_TOKEN
                if max_chars > 0:
                    truncated = text[:max_chars] + "\n... [truncated]"
                    fitted.append((filename, truncated))
                # Budget is now exhausted either way
                remaining = 0

        total_used = budget - remaining
        return fitted, total_used
