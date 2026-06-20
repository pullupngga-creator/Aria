"""Context injection engine for Aria — @-mention parsing and source assembly."""

from aria.context.injector import ContextInjector, TokenBudget
from aria.context.mention import detect_active_trigger, find_mentions, search_documents

__all__ = [
    "ContextInjector",
    "TokenBudget",
    "detect_active_trigger",
    "find_mentions",
    "search_documents",
]
