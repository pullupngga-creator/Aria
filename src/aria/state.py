"""Global application state management for Aria."""

from collections.abc import Callable
from typing import Any


class AppState:
    """Singleton state manager for reactive application state."""

    _instance: "AppState | None" = None
    _initialized: bool

    def __new__(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # Vault state
        self.documents: list[dict[str, Any]] = []
        self.active_document_ids: set[str] = set()

        # Chat state
        self.current_conversation_id: str | None = None
        self.messages: list[dict[str, Any]] = []

        # UI state
        self.vault_panel_width: float = 320.0
        self.vault_collapsed: bool = False
        self.is_vault_search_visible: bool = False
        self.search_query: str = ""

        # Observers for reactive updates
        self._observers: dict[str, list[Callable[[], None]]] = {}

        self._initialized = True

    def add_observer(self, event: str, callback: Callable[[], None]) -> None:
        """Add an observer for state changes."""
        if event not in self._observers:
            self._observers[event] = []
        self._observers[event].append(callback)

    def remove_observer(self, event: str, callback: Callable[[], None]) -> None:
        """Remove an observer for state changes."""
        if event in self._observers:
            self._observers[event] = [cb for cb in self._observers[event] if cb != callback]

    def _notify_observers(self, event: str) -> None:
        """Notify all observers of a state change."""
        if event in self._observers:
            for callback in self._observers[event]:
                try:
                    callback()
                except Exception:
                    pass  # Silently handle observer errors

    def add_document(self, document: dict[str, Any]) -> None:
        """Add a document to the vault."""
        self.documents.append(document)
        self._notify_observers("documents_changed")

    def remove_document(self, document_id: str) -> None:
        """Remove a document from the vault."""
        self.documents = [d for d in self.documents if d["id"] != document_id]
        self.active_document_ids.discard(document_id)
        self._notify_observers("documents_changed")

    def toggle_document_active(self, document_id: str) -> None:
        """Toggle a document's active state."""
        if document_id in self.active_document_ids:
            self.active_document_ids.remove(document_id)
        else:
            self.active_document_ids.add(document_id)
        self._notify_observers("active_documents_changed")

    def is_document_active(self, document_id: str) -> bool:
        """Check if a document is active."""
        return document_id in self.active_document_ids

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to the current conversation."""
        self.messages.append(message)
        self._notify_observers("messages_changed")

    def clear_messages(self) -> None:
        """Clear all messages."""
        self.messages = []
        self._notify_observers("messages_changed")

    def set_vault_panel_width(self, width: float) -> None:
        """Update vault panel width."""
        self.vault_panel_width = max(240.0, min(480.0, width))
        self._notify_observers("vault_width_changed")

    def toggle_vault_collapsed(self) -> None:
        """Toggle the vault sidebar collapsed state."""
        self.vault_collapsed = not self.vault_collapsed
        self._notify_observers("vault_collapsed_changed")


# Global state instance
app_state: AppState = AppState()
