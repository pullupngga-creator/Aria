"""Token budget bar UI component for displaying context window usage."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import flet as ft

from aria.ui.theme import COLORS, TYPOGRAPHY

if TYPE_CHECKING:
    from aria.context.injector import TokenUsage

logger = logging.getLogger(__name__)

# Utilization thresholds for color coding
_THRESHOLD_WARNING: float = 0.70
_THRESHOLD_ERROR: float = 0.90


def _format_tokens(n: int) -> str:
    """Format token count for display (e.g., 1234 -> '1.2K', 128000 -> '128K')."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _utilization_color(utilization: float) -> str:
    """Return the appropriate color for a utilization level."""
    if utilization >= _THRESHOLD_ERROR:
        return COLORS["accent_error"]
    if utilization >= _THRESHOLD_WARNING:
        return COLORS["accent_warning"]
    return COLORS["accent_success"]


class TokenBudgetBar(ft.Container):
    """Thin horizontal progress bar displaying context window token usage.

    Placed between the message area and the InputBar.  Shows:
    - A colored progress bar (green < 70%, yellow 70-89%, red >= 90%)
    - A label: "42.3K / 128K tokens"
    - A tooltip with the full breakdown on hover

    Initially hidden until `update_usage()` is called.
    """

    def __init__(self) -> None:
        """Initialize the token budget bar."""
        super().__init__()

        # ── Progress bar ────────────────────────────────────────────────────
        self._progress_bar = ft.ProgressBar(
            value=0.0,
            color=COLORS["accent_success"],
            bgcolor=COLORS["bg_hover"],
        )

        self._progress_container = ft.Container(
            content=self._progress_bar,
            height=3,
            border_radius=2,
        )

        # ── Label ───────────────────────────────────────────────────────────
        self._label = ft.Text(
            "",
            color=COLORS["text_muted"],
            size=TYPOGRAPHY["micro"]["size"],
        )

        # ── Layout ──────────────────────────────────────────────────────────
        self.content = ft.Column(
            [
                self._progress_container,
                ft.Container(
                    content=self._label,
                    alignment=ft.Alignment(1, 0),
                    padding=ft.Padding(left=0, right=4, top=2, bottom=0),
                ),
            ],
            spacing=0,
        )

        self.padding = ft.Padding(left=16, right=16, top=4, bottom=0)
        self.visible = False  # Hidden until usage is calculated

    # ── Public API ──────────────────────────────────────────────────────────────

    def update_usage(self, usage: TokenUsage) -> None:
        """Update the bar with a new token usage breakdown.

        Shows the bar if it was hidden and updates the progress, label,
        color, and tooltip based on the provided usage data.

        Args:
            usage: TokenUsage namedtuple from ContextInjector.calculate_usage().
        """
        # Show the bar when there's any usage to display
        self.visible = usage.total_used > 0 or usage.document_count > 0

        # Update progress bar
        # Clamp value to [0.0, 1.0] for ProgressBar rendering
        bar_value = max(0.0, min(1.0, usage.utilization))
        self._progress_bar.value = bar_value
        self._progress_bar.color = _utilization_color(usage.utilization)

        # Update label
        used_str = _format_tokens(usage.total_used)
        limit_str = _format_tokens(usage.context_limit)
        self._label.value = f"{used_str} / {limit_str} tokens"
        self._label.color = _utilization_color(usage.utilization)

        # Build tooltip with full breakdown
        tooltip_parts = [
            f"Base: {_format_tokens(usage.base_prompt_tokens)}",
            f"Sources: {_format_tokens(usage.source_tokens)} ({usage.document_count} docs)",
            f"Message: {_format_tokens(usage.user_message_tokens)}",
            f"History: {_format_tokens(usage.history_tokens)}",
            f"Reserved: {_format_tokens(usage.reserved_tokens)}",
        ]
        self.tooltip = " | ".join(tooltip_parts)

        try:
            self.update()
        except (AssertionError, RuntimeError):
            # Control not yet mounted; safe to ignore during init.
            pass

    def reset(self) -> None:
        """Hide the bar and reset to initial state."""
        self.visible = False
        self._progress_bar.value = 0.0
        self._progress_bar.color = COLORS["accent_success"]
        self._label.value = ""
        self._label.color = COLORS["text_muted"]
        self.tooltip = None
        try:
            self.update()
        except (AssertionError, RuntimeError):
            pass
