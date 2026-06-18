"""Chat input bar with auto-expanding textarea and send button."""

from collections.abc import Callable
from typing import Any

import flet as ft

from aria.ui.theme import COLORS, TYPOGRAPHY


class InputBar(ft.Container):
    """Fixed-bottom input bar for composing and sending messages.

    Features:
    - Auto-expanding textarea (1-6 lines)
    - Enter to send, Shift+Enter for newline
    - Send button with electric-blue icon
    - Live character count display
    - Disabled state during API calls
    """

    def __init__(self, on_send: Callable[[str], None]) -> None:
        """Initialize the input bar.

        Args:
            on_send: Callback invoked with trimmed input text when the user sends.
        """
        super().__init__()
        self._on_send = on_send
        self._enabled: bool = True

        # Character counter label
        self._char_counter = ft.Text(
            "0 chars",
            color=COLORS["text_muted"],
            size=TYPOGRAPHY["micro"]["size"],
        )

        # Main text input
        self._text_field = ft.TextField(
            hint_text="Ask Aria anything...",
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

        # Send button
        self._send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=COLORS["accent_electric"],
            icon_size=20,
            tooltip="Send message",
            on_click=self._handle_send_click,
        )

        # Layout: [text_field] [send_btn] with char counter below
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

    def _handle_submit(self, e: Any) -> None:
        """Handle Enter key press (on_submit from TextField)."""
        self._send()

    def _handle_send_click(self, e: Any) -> None:
        """Handle send button click."""
        self._send()

    def _handle_change(self, e: Any) -> None:
        """Update character counter on each keystroke."""
        text = self._text_field.value or ""
        char_count = len(text)
        self._char_counter.value = f"{char_count} chars"
        self._char_counter.update()

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
