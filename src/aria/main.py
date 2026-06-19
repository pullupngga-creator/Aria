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

from aria.api.gemini import GeminiClient
from aria.chat import history as chat_history
from aria.config import settings
from aria.db import init_db
from aria.exceptions import AriaError
from aria.state import app_state
from aria.ui.app import TwoPanelShell
from aria.ui.chat_panel import ChatPanel
from aria.ui.theme import COLORS, build_theme
from aria.ui.vault_panel import VaultPanel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(page: ft.Page) -> None:
    """Initialize and run the Aria application."""

    try:
        # Initialise database on first launch (idempotent — sync, one-time)
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

        # ── Load persisted conversations (async) ──────────────────────────
        conversations = await chat_history.get_conversations()
        app_state.load_conversations(conversations)

        # Auto-select the most recently updated conversation (if any)
        if conversations:
            latest = conversations[0]  # get_conversations() orders by updated_at DESC
            latest_id: str = str(latest["id"])
            messages = await chat_history.get_messages(latest_id)
            app_state.set_current_conversation(latest_id)
            app_state.load_messages(messages)
            logger.info(
                "Restored conversation %s with %d message(s)", latest_id, len(messages)
            )

        # ── Collapse toggle callback ──────────────────────────────────────────
        def _on_toggle(e: Any) -> None:
            app_state.toggle_vault_collapsed()

        # ── Vault panel (left) ────────────────────────────────────────────────
        vault_panel = VaultPanel(page=page, on_collapse_toggle=_on_toggle)

        # ── Chat panel (right) ────────────────────────────────────────────────
        def _llm_factory() -> GeminiClient:
            """Lazy factory: creates GeminiClient only when first message is sent."""
            return GeminiClient(api_key=settings.gemini_api_key or "")

        chat_panel = ChatPanel(
            page=page,
            on_collapse_toggle=_on_toggle,
            llm_client_factory=_llm_factory,
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
