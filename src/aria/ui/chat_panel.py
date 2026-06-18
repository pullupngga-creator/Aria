"""AI Chat Canvas panel with message list and send orchestration."""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import flet as ft

from aria.api.base import LLMClient
from aria.chat import history as chat_history
from aria.document.vault import VaultManager
from aria.exceptions import APIError
from aria.state import app_state
from aria.ui.input_bar import InputBar
from aria.ui.message_bubble import LoadingIndicator, MessageBubble
from aria.ui.theme import COLORS, TYPOGRAPHY
from aria.ui.vault_panel import ToastNotification

logger = logging.getLogger(__name__)

# System prompt template
_SYSTEM_PROMPT_BASE = (
    "You are Aria, a knowledgeable research assistant. "
    "You help users analyze documents, answer questions, and think critically. "
    "Be concise, accurate, and cite sources when referencing provided documents."
)


class ChatPanel(ft.Column):
    """Right-hand chat canvas: header + scrollable messages + input bar.

    Orchestrates the send flow between the UI, AppState, persistence, and the LLM client.
    """

    def __init__(
        self,
        page: ft.Page,
        on_collapse_toggle: Callable[[Any], Any],
        llm_client_factory: Callable[[], LLMClient],
    ) -> None:
        """Initialize the chat panel.

        Args:
            page: The Flet page (used for run_thread and run_task).
            on_collapse_toggle: Callback to toggle the vault sidebar.
            llm_client_factory: Callable that returns a fresh LLMClient instance.
                                Called lazily on first send to defer key validation.
        """
        super().__init__()
        self._page = page
        self._on_collapse_toggle = on_collapse_toggle
        self._llm_client_factory = llm_client_factory
        self._llm_client: LLMClient | None = None
        self._vault_manager = VaultManager()
        self.toasts: list[ToastNotification] = []

        self.expand = True
        self.spacing = 0

        # ── Header ──────────────────────────────────────────────────────────────
        self._expand_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_ROUNDED,
            icon_color=COLORS["text_muted"],
            icon_size=18,
            tooltip="Expand sidebar",
            visible=app_state.vault_collapsed,
            on_click=self._on_collapse_toggle,
        )

        self._header = ft.Container(
            content=ft.Row(
                controls=[
                    self._expand_btn,
                    ft.Text(
                        "AI Chat Canvas",
                        size=TYPOGRAPHY["h1"]["size"],
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_primary"],
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.ADD_COMMENT_OUTLINED,
                        icon_color=COLORS["text_secondary"],
                        icon_size=20,
                        tooltip="New chat",
                        on_click=self._on_new_chat,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.Padding(left=8, right=16, top=12, bottom=12),
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border_hairline"])),
        )

        # ── Empty state ─────────────────────────────────────────────────────────
        self._empty_state = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                        color=COLORS["accent_electric"],
                        size=56,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "Welcome to Aria",
                        size=TYPOGRAPHY["display"]["size"],
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_primary"],
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Upload documents to the vault, activate sources, and ask anything.",
                        size=TYPOGRAPHY["body"]["size"],
                        color=COLORS["text_secondary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment(0, -0.5),
            expand=True,
            padding=48,
            visible=True,
        )

        # ── Message list ────────────────────────────────────────────────────────
        self._message_list = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding(left=0, right=0, top=8, bottom=8),
            auto_scroll=True,
        )

        self._loading_indicator = LoadingIndicator()

        # Message area container (stacks messages + loading indicator)
        self._message_area = ft.Container(
            content=ft.Column(
                [
                    self._message_list,
                    self._loading_indicator,
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            visible=False,  # Hidden until there are messages
        )

        # ── Toast container (overlaid on the content area) ────────────────────
        self._toast_container = ft.Column(
            [],
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )
        self._toast_stack = ft.Container(
            content=self._toast_container,
            alignment=ft.Alignment(1, 1),
            padding=ft.Padding(left=16, top=16, right=16, bottom=16),
        )

        # ── Input bar ───────────────────────────────────────────────────────────
        self._input_bar = InputBar(on_send=self._handle_send)

        # ── Assemble main content ───────────────────────────────────────────────
        # Use a Column (not Stack) so expand is properly distributed:
        #   header (fixed) → content_area (expands) → input_bar (fixed)
        self._content_area = ft.Stack(
            [
                ft.Column(
                    [
                        self._empty_state,
                        self._message_area,
                    ],
                    spacing=0,
                    expand=True,
                ),
                self._toast_stack,
            ],
            expand=True,
        )

        self.controls = [
            self._header,
            self._content_area,
            self._input_bar,
        ]

        # ── State observers ─────────────────────────────────────────────────────
        app_state.add_observer("vault_collapsed_changed", self._sync_expand_btn)
        app_state.add_observer("messages_changed", self._rebuild_messages)
        app_state.add_observer("sending_state_changed", self._on_sending_state_changed)

    # ── Observer callbacks ──────────────────────────────────────────────────────

    def _sync_expand_btn(self) -> None:
        """Show/hide expand button based on vault collapse state."""
        self._expand_btn.visible = app_state.vault_collapsed
        self._expand_btn.update()

    def _rebuild_messages(self) -> None:
        """Rebuild the message list from app_state.messages."""
        messages = app_state.messages
        has_messages = len(messages) > 0

        self._empty_state.visible = not has_messages
        self._message_area.visible = has_messages

        if has_messages:
            bubbles: list[ft.Control] = []
            for msg in messages:
                bubbles.append(MessageBubble(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    created_at=msg.get("created_at", ""),
                ))
            self._message_list.controls = bubbles

        self._content_area.update()

    def _on_sending_state_changed(self) -> None:
        """Update loading indicator and input bar based on sending state."""
        is_sending = app_state.is_sending
        self._loading_indicator.visible = is_sending
        self._input_bar.set_enabled(not is_sending)
        self._loading_indicator.update()
        self._input_bar.update()

    # ── Chat actions ────────────────────────────────────────────────────────────

    def _on_new_chat(self, e: Any) -> None:
        """Start a new conversation, clearing current messages."""
        app_state.set_current_conversation(None)

    # ── Send flow ───────────────────────────────────────────────────────────────

    def _handle_send(self, text: str) -> None:
        """Handle a send action from the InputBar.

        Runs the full send flow (DB write + API call) in a background thread
        to keep the UI responsive.
        """
        if app_state.is_sending:
            return
        if not text.strip():
            return

        def send_worker() -> None:
            """Background worker: persist message, call LLM, persist response."""
            try:
                app_state.set_sending(True)

                # Create conversation on first message
                if app_state.current_conversation_id is None:
                    conv_id = chat_history.create_conversation(
                        model_provider="gemini",
                        model_name="gemini-1.5-pro",
                    )
                    app_state.current_conversation_id = conv_id

                conv_id = app_state.current_conversation_id
                assert conv_id is not None  # Guaranteed by create above

                # Save user message to DB
                msg_id = chat_history.save_message(
                    conversation_id=conv_id,
                    role="user",
                    content=text,
                    token_count=len(text.split()),  # rough estimate
                )

                # Add to in-memory state (triggers UI rebuild)
                app_state.add_message({
                    "id": msg_id,
                    "role": "user",
                    "content": text,
                    "created_at": "",
                })

                # Build system prompt with active sources
                system_prompt = self._build_system_prompt()

                # Build message history for API
                api_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in app_state.messages
                    if m.get("role") in ("user", "assistant")
                ]

                # Lazy-init LLM client
                if self._llm_client is None:
                    self._llm_client = self._llm_client_factory()

                # Call the LLM (synchronous call wrapped in asyncio.run for the thread)
                response_text = asyncio.run(
                    self._llm_client.send_message(api_messages, system_prompt)
                )

                if not response_text:
                    response_text = "No response generated."

                # Save assistant message to DB
                asst_id = chat_history.save_message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=response_text,
                    token_count=len(response_text.split()),
                    model_provider="gemini",
                    model_name="gemini-1.5-pro",
                )

                # Add to in-memory state (triggers UI rebuild)
                app_state.add_message({
                    "id": asst_id,
                    "role": "assistant",
                    "content": response_text,
                    "created_at": "",
                })

            except APIError as e:
                logger.error("API error during send", exc_info=True)
                self._show_error(e.message)
            except Exception:
                logger.error("Unexpected error during send", exc_info=True)
                self._show_error("An unexpected error occurred. Please try again.")
            finally:
                app_state.set_sending(False)

        self._page.run_thread(send_worker)

    def _build_system_prompt(self) -> str:
        """Build the system prompt, injecting active source document text."""
        active_ids = app_state.active_document_ids
        if not active_ids:
            return _SYSTEM_PROMPT_BASE

        source_sections: list[str] = []
        for doc_id in active_ids:
            doc = self._vault_manager.get_document(doc_id)
            if doc is None:
                continue
            storage_path = Path(doc.storage_path)
            try:
                text = storage_path.read_text(encoding="utf-8")
                # Truncate very long documents to ~8000 chars to avoid context overflow
                if len(text) > 8000:
                    text = text[:8000] + "\n... [truncated]"
                source_sections.append(
                    f"\n--- Document: {doc.filename} ---\n{text}"
                )
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Failed to read source document %s: %s", doc_id, e)

        if not source_sections:
            return _SYSTEM_PROMPT_BASE

        sources_block = "\n".join(source_sections)
        return (
            f"{_SYSTEM_PROMPT_BASE}\n\n"
            "The following documents have been provided as context. "
            "Use them to inform your responses:\n"
            f"{sources_block}"
        )

    # ── Toast helpers ───────────────────────────────────────────────────────────

    def _show_toast(self, toast: ToastNotification) -> None:
        """Show a toast notification on the chat panel."""
        toast.on_dismiss = lambda: self._remove_toast(toast)
        self.toasts.append(toast)
        self._toast_container.controls.append(toast)
        self._toast_container.update()

        async def auto_dismiss() -> None:
            await asyncio.sleep(4)
            self._remove_toast(toast)

        self._page.run_task(auto_dismiss)

    def _remove_toast(self, toast: ToastNotification) -> None:
        """Remove a toast from the panel."""
        if toast in self.toasts:
            self.toasts.remove(toast)
        if toast in self._toast_container.controls:
            self._toast_container.controls.remove(toast)
            self._toast_container.update()

    def _show_error(self, message: str) -> None:
        """Show an error toast."""
        toast = ToastNotification(message, notification_type="error")
        self._show_toast(toast)
