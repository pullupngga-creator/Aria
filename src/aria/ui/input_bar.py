"""Chat input bar with auto-expanding textarea, send button, and @-mention support."""

import logging
from collections.abc import Callable
from typing import Any

import flet as ft

from aria.context.mention import detect_active_trigger
from aria.ui.theme import COLORS, TYPOGRAPHY

logger = logging.getLogger(__name__)


class InputBar(ft.Container):
    """Fixed-bottom input bar for composing and sending messages.

    Features:
    - Auto-expanding textarea (1–6 lines)
    - Enter to send, Shift+Enter for newline
    - Send button with electric-blue icon
    - Live character count display
    - Disabled state during API calls
    - @-mention detection: fires callbacks when an active @-trigger is found
    - Mention chips row: shows selected documents with removable × buttons
    """

    def __init__(
        self,
        on_send: Callable[[str], None],
        on_mention_trigger: Callable[[str], None] | None = None,
        on_mention_dismiss: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the input bar.

        Args:
            on_send: Callback invoked with trimmed input text when the user sends.
            on_mention_trigger: Called with the query string (without @) whenever
                the user is typing an active @-mention.
            on_mention_dismiss: Called when the active @-mention trigger ends
                (user typed a space, deleted the @, or a mention was selected).
        """
        super().__init__()
        self._on_send = on_send
        self._on_mention_trigger = on_mention_trigger
        self._on_mention_dismiss = on_mention_dismiss
        self._enabled: bool = True

        # ── @-mention state ──────────────────────────────────────────────────
        self._mentioned_docs: list[dict[str, Any]] = []
        self._mention_trigger_active: bool = False
        # Set externally by ChatPanel when its dropdown is open.
        # When True, _send() is suppressed so Enter selects from the dropdown
        # rather than dispatching a message.
        self.is_mention_dropdown_open: bool = False

        # ── Character counter ────────────────────────────────────────────────
        self._char_counter = ft.Text(
            "0 chars",
            color=COLORS["text_muted"],
            size=TYPOGRAPHY["micro"]["size"],
        )

        # ── Main text input ──────────────────────────────────────────────────
        self._text_field = ft.TextField(
            hint_text="Ask Aria anything, or type @ to mention a source…",
            multiline=True,
            min_lines=1,
            max_lines=6,
            border_radius=8,
            bgcolor=COLORS["bg_obsidian"],
            color=COLORS["text_primary"],
            hint_style=ft.TextStyle(color=COLORS["text_muted"]),
            border_color=COLORS["border_subtle"],
            focused_border_color=COLORS["border_focus"],
            content_padding=ft.Padding(left=12, right=12, top=10, bottom=10),
            text_size=TYPOGRAPHY["body"]["size"],
            expand=True,
            on_submit=self._handle_submit,
            on_change=self._handle_change,
        )

        # ── Send button ──────────────────────────────────────────────────────
        self._send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=COLORS["accent_electric"],
            icon_size=20,
            tooltip="Send message",
            on_click=self._handle_send_click,
        )

        # ── Mention chips row (hidden until mentions are added) ──────────────
        self._chips_row = ft.Row(
            [],
            wrap=True,
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self._chips_container = ft.Container(
            content=self._chips_row,
            padding=ft.Padding(left=4, right=4, top=4, bottom=0),
            visible=False,
        )

        # ── Input row: [text_field] [send_btn] ───────────────────────────────
        input_row = ft.Row(
            [
                self._text_field,
                ft.Container(
                    content=self._send_button,
                    width=36,
                    height=36,
                    alignment=ft.Alignment(0, 0),
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=8,
        )

        self.content = ft.Column(
            [
                self._chips_container,
                input_row,
                ft.Container(
                    content=self._char_counter,
                    alignment=ft.Alignment(1, 0),
                    padding=ft.Padding(left=0, right=4, top=4, bottom=0),
                ),
            ],
            spacing=0,
        )

        self.bgcolor = COLORS["bg_elevated"]
        self.border = ft.Border(top=ft.BorderSide(1, COLORS["border_hairline"]))
        self.padding = ft.Padding(left=16, right=16, top=12, bottom=12)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _handle_submit(self, e: Any) -> None:
        """Handle Enter key press (on_submit from TextField).

        If the mention dropdown is open, suppress send — ChatPanel's keyboard
        handler will consume the Enter key to select from the dropdown.
        """
        if self.is_mention_dropdown_open:
            # Enter is being consumed by the mention dropdown via page-level
            # keyboard handler.  Suppress the send action here.
            return
        self._send()

    def _handle_send_click(self, e: Any) -> None:
        """Handle send button click."""
        if self.is_mention_dropdown_open:
            return
        self._send()

    def _handle_change(self, e: Any) -> None:
        """Update character counter and detect @-mention triggers."""
        text = self._text_field.value or ""

        # Update character counter
        char_count = len(text)
        self._char_counter.value = f"{char_count} chars"
        self._char_counter.update()

        # ── @-mention trigger detection ──────────────────────────────────────
        trigger_query = detect_active_trigger(text)

        if trigger_query is not None:
            # An active @-mention is in progress
            self._mention_trigger_active = True
            if self._on_mention_trigger is not None:
                self._on_mention_trigger(trigger_query)
        elif self._mention_trigger_active:
            # Trigger disappeared (user typed space, deleted @, etc.)
            self._mention_trigger_active = False
            if self._on_mention_dismiss is not None:
                self._on_mention_dismiss()

    def _send(self) -> None:
        """Fire the on_send callback with trimmed input, then clear the field."""
        if not self._enabled:
            return
        text = (self._text_field.value or "").strip()
        if not text:
            return
        self._on_send(text)
        self._text_field.value = ""
        self._text_field.update()
        self._char_counter.value = "0 chars"
        self._char_counter.update()
        # Clear mention chips after send
        self.clear_mentions()

    # ── @-mention public API ────────────────────────────────────────────────────

    def add_mention(self, document: dict[str, Any]) -> None:
        """Add a mention chip and replace the active @query text with @filename.

        Called by ChatPanel when the user selects a document from the dropdown.

        Args:
            document: Document dict with at least "id" and "filename" keys.
        """
        doc_id = document.get("id", "")
        filename = document.get("filename", "unknown")

        # Guard against duplicate mentions
        if any(d.get("id") == doc_id for d in self._mentioned_docs):
            # Still reset the trigger state
            self._reset_mention_trigger()
            return

        # Store the document
        self._mentioned_docs.append(document)

        # Replace the active @query in the text field with @filename
        text = self._text_field.value or ""
        query = detect_active_trigger(text)
        if query is not None:
            # Find the position of @ in the text
            at_pos = text.rfind("@")
            if at_pos >= 0:
                new_text = text[:at_pos] + "@" + filename + " "
                self._text_field.value = new_text
                self._text_field.update()

        # Build and add a chip
        chip = self._build_chip(document)
        self._chips_row.controls.append(chip)
        self._chips_container.visible = True
        self._chips_container.update()

        # Update character counter (text changed)
        char_count = len(self._text_field.value or "")
        self._char_counter.value = f"{char_count} chars"
        self._char_counter.update()

        # Reset trigger state and fire dismiss to close the dropdown
        self._reset_mention_trigger()

    @property
    def mentioned_document_ids(self) -> list[str]:
        """Return IDs of documents mentioned in the current input."""
        return [d.get("id", "") for d in self._mentioned_docs if d.get("id")]

    def clear_mentions(self) -> None:
        """Remove all mention chips and reset mention state.

        Called after a message is sent so the next message starts clean.
        """
        self._mentioned_docs = []
        self._chips_row.controls = []
        self._chips_container.visible = False
        try:
            self._chips_container.update()
        except (AssertionError, RuntimeError):
            # Control not yet mounted; safe to ignore during init / teardown.
            pass

    # ── Private helpers ─────────────────────────────────────────────────────────

    def _reset_mention_trigger(self) -> None:
        """Reset the trigger flag and fire on_mention_dismiss to close dropdown."""
        self._mention_trigger_active = False
        if self._on_mention_dismiss is not None:
            self._on_mention_dismiss()

    def _build_chip(self, document: dict[str, Any]) -> ft.Container:
        """Build a removable mention chip for a document."""
        doc_id = document.get("id", "")
        filename = document.get("filename", "?")

        chip_label = ft.Text(
            f"@{filename}",
            color=COLORS["text_inverse"],
            size=TYPOGRAPHY["micro"]["size"],
            weight=ft.FontWeight.W_500,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        remove_btn = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_color=COLORS["text_inverse"],
            icon_size=12,
            tooltip="Remove mention",
            on_click=lambda _e, did=doc_id: self._remove_mention(did),
            style=ft.ButtonStyle(padding=0),
        )

        chip_row = ft.Row(
            [chip_label, remove_btn],
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        )

        return ft.Container(
            content=chip_row,
            bgcolor=COLORS["accent_electric"],
            border_radius=6,
            padding=ft.Padding(left=8, right=4, top=2, bottom=2),
            data=doc_id,  # used to find this chip when removing
        )

    def _remove_mention(self, doc_id: str) -> None:
        """Remove a mention chip and its document from the internal list."""
        self._mentioned_docs = [d for d in self._mentioned_docs if d.get("id") != doc_id]

        # Remove the matching chip from the row
        self._chips_row.controls = [
            c
            for c in self._chips_row.controls
            if not (isinstance(c, ft.Container) and getattr(c, "data", None) == doc_id)
        ]

        # Hide chips container if empty
        if not self._chips_row.controls:
            self._chips_container.visible = False

        try:
            self._chips_container.update()
        except (AssertionError, RuntimeError):
            pass

    # ── Enable / disable / focus ────────────────────────────────────────────────

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the input bar (e.g., during API calls).

        Args:
            enabled: True to enable, False to disable.
        """
        self._enabled = enabled
        self._text_field.read_only = not enabled
        self._text_field.color = COLORS["text_primary"] if enabled else COLORS["text_muted"]
        self._send_button.icon_color = (
            COLORS["accent_electric"] if enabled else COLORS["text_muted"]
        )
        self._text_field.update()
        self._send_button.update()

    def focus(self) -> None:
        """Set focus to the text field."""
        self._text_field.focus()
