"""Message bubble rendering for user and assistant messages."""

import flet as ft

from aria.ui.theme import COLORS, TYPOGRAPHY


class MessageBubble(ft.Container):
    """Renders a single chat message with role-based styling.

    - User messages: right-aligned, bg_elevated background, max-width 80%
    - Assistant messages: left-aligned, full-width
    - Timestamp shown in muted micro typography below each message
    """

    def __init__(self, role: str, content: str, created_at: str = "") -> None:
        """Initialize a message bubble.

        Args:
            role: Message role ('user' or 'assistant').
            content: Raw message text.
            created_at: Optional timestamp string for display.
        """
        super().__init__()
        self._role = role
        self._content = content

        # Format timestamp for display
        timestamp_display = self._format_timestamp(created_at)

        # Message text
        message_text = ft.Text(
            content,
            color=COLORS["text_primary"],
            size=TYPOGRAPHY["body"]["size"],
            weight=ft.FontWeight.W_400,
        )

        # Timestamp label
        timestamp_label = ft.Text(
            timestamp_display,
            color=COLORS["text_muted"],
            size=TYPOGRAPHY["micro"]["size"],
        )

        # Inner column: message + timestamp
        inner = ft.Column(
            [
                message_text,
                ft.Container(height=4),
                timestamp_label,
            ],
            spacing=0,
        )

        # Role icon for assistant messages
        if role == "assistant":
            role_indicator = ft.Icon(
                icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                color=COLORS["accent_electric"],
                size=16,
            )
            header_row = ft.Row(
                [role_indicator, ft.Text(
                    "Aria",
                    color=COLORS["text_secondary"],
                    size=TYPOGRAPHY["small"]["size"],
                    weight=ft.FontWeight.W_500,
                )],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            inner.controls.insert(0, header_row)
            inner.controls.insert(1, ft.Container(height=6))

        if role == "user":
            # User message: right-aligned, elevated background, max-width 80%
            self.content = ft.Row(
                [
                    ft.Container(expand=True),  # Spacer to push right
                    ft.Container(
                        content=inner,
                        bgcolor=COLORS["bg_elevated"],
                        border_radius=8,
                        padding=ft.Padding(left=14, right=14, top=10, bottom=10),
                        width=None,
                        max_width=600,  # ~80% of typical canvas width
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            )
        else:
            # Assistant message: left-aligned, full-width
            self.content = ft.Container(
                content=inner,
                padding=ft.Padding(left=4, right=16, top=8, bottom=8),
            )

        self.padding = ft.Padding(left=16, right=16, top=4, bottom=4)

    @staticmethod
    def _format_timestamp(created_at: str) -> str:
        """Format an ISO timestamp into a short human-readable string.

        Returns empty string if parsing fails or input is empty.
        """
        if not created_at:
            return ""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created_at)
            return dt.strftime("%I:%M %p")
        except (ValueError, TypeError):
            return created_at[:16] if created_at else ""


class LoadingIndicator(ft.Container):
    """A small pulsing loading indicator shown while waiting for an API response."""

    def __init__(self) -> None:
        super().__init__()
        self.content = ft.Row(
            [
                ft.ProgressRing(
                    width=16,
                    height=16,
                    stroke_width=2,
                    color=COLORS["accent_electric"],
                ),
                ft.Container(width=8),
                ft.Text(
                    "Aria is thinking...",
                    color=COLORS["text_secondary"],
                    size=TYPOGRAPHY["small"]["size"],
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.padding = ft.Padding(left=20, right=16, top=8, bottom=8)
        self.visible = False
