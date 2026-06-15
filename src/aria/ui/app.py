"""Main application layout with collapsible vault sidebar."""

import flet as ft

from aria.state import app_state
from aria.ui.theme import COLORS

_SIDEBAR_WIDTH: float = 320.0
_ANIMATION_DURATION: int = 300  # ms


class TwoPanelShell(ft.Row):
    """Main application shell with collapsible Vault (left) and Canvas (right) panels."""

    def __init__(self, vault_panel: ft.Control, chat_panel: ft.Control) -> None:
        super().__init__()
        self.vault_panel = vault_panel
        self.chat_panel = chat_panel
        self.expand = True
        self.spacing = 0

        # Observe collapse state changes
        app_state.add_observer("vault_collapsed_changed", self._on_collapsed_changed)

        self.left_panel = ft.Container(
            content=self.vault_panel,
            width=_SIDEBAR_WIDTH,
            bgcolor=COLORS["bg_obsidian"],
            border=ft.Border(right=ft.BorderSide(1, COLORS["border_hairline"])),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            animate=ft.Animation(_ANIMATION_DURATION, ft.AnimationCurve.DECELERATE),
        )

        self.right_panel = ft.Container(
            content=self.chat_panel,
            expand=True,
            bgcolor=COLORS["bg_anthracite"],
        )

        self.controls = [
            self.left_panel,
            self.right_panel,
        ]

    def _on_collapsed_changed(self) -> None:
        """Animate the vault sidebar open or closed."""
        if app_state.vault_collapsed:
            self.left_panel.width = 0
            self.left_panel.border = None
        else:
            self.left_panel.width = _SIDEBAR_WIDTH
            self.left_panel.border = ft.Border(right=ft.BorderSide(1, COLORS["border_hairline"]))
        self.left_panel.update()
