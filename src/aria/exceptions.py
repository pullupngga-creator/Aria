"""Custom exceptions for Aria application."""


class AriaError(Exception):
    """Base exception for all Aria-specific errors."""

    def __init__(self, message: str, *, context: dict[str, str] | None = None) -> None:
        """Initialize Aria error with message and optional context."""
        self.message = message
        self.context = context or {}
        super().__init__(self.message)


class DocumentParseError(AriaError):
    """Raised when document parsing fails."""

    pass


class FileSizeExceededError(AriaError):
    """Raised when file exceeds 50MB limit."""

    pass


class UnsupportedFileTypeError(AriaError):
    """Raised for non-PDF/TXT files in Phase 0."""

    pass


class VaultError(AriaError):
    """Raised when vault operations fail."""

    pass


class ContextError(AriaError):
    """Raised when context injection fails."""

    pass


class APIError(AriaError):
    """Raised when LLM API calls fail."""

    pass


class StateError(AriaError):
    """Raised when state management operations fail."""

    pass


class ConfigurationError(AriaError):
    """Raised when configuration is invalid or missing."""

    pass
