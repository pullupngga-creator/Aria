"""Entry point for Aria desktop application."""

import logging
import os
import sys

import flet as ft

# This finds the folder your app is running from and adds it to Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from typing import Any

from aria.config import settings
from aria.db import init_db
from aria.exceptions import AriaError
from aria.state import app_state
from aria.ui.app import TwoPanelShell
from aria.ui.theme import COLORS, TYPOGRAPHY, build_theme
from aria.ui.vault_panel import VaultPanel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main(page: ft.Page) -> None:
    """Initialize and run the Aria application."""

    try:
        # Initialise database on first launch (idempotent)
        init_db()

        # Page configuration
        page.title = f"{settings.app_name} v{settings.app_version}"
        page.theme_mode = ft.ThemeMode.DARK

        # Configure fonts from remote URLs
        page.fonts = {
            "Geist": "https://raw.githubusercontent.com/vercel/geist-font/main/packages/next/dist/fonts/geist/Geist-Regular.ttf",
            "JetBrains Mono": "https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
        }
        page.theme = build_theme()
        page.dark_theme = build_theme()

        page.window.min_width = settings.min_window_width
        page.window.min_height = settings.min_window_height
        page.window.width = settings.default_window_width
        page.window.height = settings.default_window_height
        page.bgcolor = COLORS["bg_anthracite"]
        page.padding = 0

        logger.info(f"Initializing {settings.app_name} v{settings.app_version}")

        # ── Collapse toggle callback ──────────────────────────────────────────
        def _on_toggle(e: Any) -> None:
            app_state.toggle_vault_collapsed()

        # ── Vault panel (left) ────────────────────────────────────────────────
        vault_panel = VaultPanel(page=page, on_collapse_toggle=_on_toggle)

        # ── Chat panel (right) ────────────────────────────────────────────────
        #   Header row: expand button (visible only when sidebar is collapsed) + title
        expand_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_ROUNDED,
            icon_color=COLORS["text_muted"],
            icon_size=18,
            tooltip="Expand sidebar",
            visible=app_state.vault_collapsed,
            on_click=_on_toggle,
        )

        def _sync_expand_btn() -> None:
            expand_btn.visible = app_state.vault_collapsed
            expand_btn.update()

        app_state.add_observer("vault_collapsed_changed", _sync_expand_btn)

        chat_header = ft.Container(
            content=ft.Row(
                controls=[
                    expand_btn,
                    ft.Text(
                        "AI Chat Canvas",
                        size=TYPOGRAPHY["h1"]["size"],
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_primary"],
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.Padding(left=8, right=16, top=12, bottom=12),
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border_hairline"])),
        )

        chat_panel = ft.Column(
            controls=[
                chat_header,
                ft.Container(
                    content=ft.Text(
                        "Welcome to Aria",
                        size=TYPOGRAPHY["display"]["size"],
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_primary"],
                    ),
                    alignment=ft.Alignment(0, -0.7),
                    expand=True,
                    padding=48,
                ),
            ],
            spacing=0,
            expand=True,
        )

        # Create two-panel shell
        shell = TwoPanelShell(vault_panel, chat_panel)

        # Add shell to page
        page.add(shell)

        logger.info("Application initialized successfully")

    except AriaError as e:
        logger.error(f"Aria error during initialization: {e.message}", extra={"context": e.context})
        error_dialog = ft.AlertDialog(
            title=ft.Text("Initialization Error"),
            content=ft.Text(e.message),
        )
        page.overlay.append(error_dialog)
        error_dialog.open = True
        page.update()
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}", exc_info=True)
        error_dialog = ft.AlertDialog(
            title=ft.Text("Unexpected Error"),
            content=ft.Text(f"An unexpected error occurred: {e}"),
        )
        page.overlay.append(error_dialog)
        error_dialog.open = True
        page.update()


if __name__ == "__main__":
    ft.run(main)
