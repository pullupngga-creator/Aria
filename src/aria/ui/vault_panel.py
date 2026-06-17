"""Sources Vault panel component with document upload and list."""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import flet as ft

from aria.document.vault import VaultManager
from aria.exceptions import FileSizeExceededError, UnsupportedFileTypeError, VaultError
from aria.state import app_state
from aria.ui.theme import COLORS, TYPOGRAPHY

logger = logging.getLogger(__name__)


class ToastNotification(ft.Container):
    """Toast notification for success/error feedback."""

    def __init__(
        self,
        message: str,
        notification_type: str = "success",
        on_dismiss: Callable[[], Any] | None = None,
    ) -> None:
        """Initialize toast notification."""
        super().__init__()
        self.message = message
        self.notification_type = notification_type
        self.on_dismiss = on_dismiss

        # Set border color based on type
        border_color = {
            "success": COLORS["accent_success"],
            "error": COLORS["accent_error"],
            "warning": COLORS["accent_warning"],
            "info": COLORS["accent_electric"],
        }.get(notification_type, COLORS["accent_electric"])

        self.bgcolor = COLORS["bg_elevated"]
        self.border = ft.Border(left=ft.BorderSide(3, border_color))
        self.border_radius = 8
        self.padding = 12
        self.margin = ft.Margin(left=0, top=0, right=0, bottom=8)
        self.shadow = ft.BoxShadow(
            blur_radius=24,
            spread_radius=0,
            color="#66000000",
            offset=ft.Offset(0, 8),
        )

        self.content = ft.Row(
            [
                ft.Icon(
                    icon=ft.Icons.CHECK_CIRCLE
                    if notification_type == "success"
                    else ft.Icons.ERROR,
                    color=border_color,
                    size=20,
                ),
                ft.Container(
                    width=8,
                ),
                ft.Text(
                    message,
                    color=COLORS["text_primary"],
                    size=TYPOGRAPHY["small"]["size"],
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=COLORS["text_secondary"],
                    icon_size=16,
                    on_click=self._dismiss,
                    tooltip="Dismiss",
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

    def _dismiss(self, e: Any) -> None:
        """Dismiss the toast notification."""
        if self.on_dismiss:
            self.on_dismiss()
        self.visible = False
        self.update()


class UploadZone(ft.Container):
    """Upload zone for documents (button click)."""

    def __init__(self, on_upload_click: Callable[[Any], Any]) -> None:
        """Initialize upload zone."""
        super().__init__()

        self.bgcolor = COLORS["bg_obsidian"]
        border_side = ft.BorderSide(2, COLORS["border_hairline"])
        self.border = ft.Border(
            top=border_side,
            right=border_side,
            bottom=border_side,
            left=border_side,
        )
        self.border_radius = 8
        self.padding = 32
        self.alignment = ft.Alignment(0, 0)
        self.expand = True

        self.content = ft.Column(
            [
                ft.Icon(
                    icon=ft.Icons.UPLOAD_FILE,
                    color=COLORS["accent_electric"],
                    size=48,
                ),
                ft.Container(height=16),
                ft.Text(
                    "Upload Documents",
                    color=COLORS["text_primary"],
                    size=TYPOGRAPHY["h2"]["size"],
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(height=8),
                ft.Text(
                    "PDF and TXT files only (max 50MB)",
                    color=COLORS["text_secondary"],
                    size=TYPOGRAPHY["small"]["size"],
                ),
                ft.Container(height=24),
                ft.ElevatedButton(
                    "Browse Files",
                    icon=ft.Icons.FOLDER_OPEN,
                    color=COLORS["text_inverse"],
                    bgcolor=COLORS["accent_electric"],
                    on_click=on_upload_click,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )


class VaultPanel(ft.Column):
    """Sources Vault panel with document list and upload functionality."""

    def __init__(self, page: ft.Page, on_collapse_toggle: Callable[[Any], Any]) -> None:
        """Initialize vault panel."""
        super().__init__()
        self._page = page
        self.vault_manager = VaultManager()
        self.toasts: list[ToastNotification] = []

        self.expand = True
        self.spacing = 0

        collapse_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT_ROUNDED,
            icon_color=COLORS["text_muted"],
            icon_size=18,
            tooltip="Collapse sidebar",
            on_click=on_collapse_toggle,
        )

        # Header
        self.header = ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        "Sources Vault",
                        color=COLORS["text_primary"],
                        size=TYPOGRAPHY["h1"]["size"],
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.ADD,
                        icon_color=COLORS["accent_electric"],
                        icon_size=32,
                        tooltip="Upload Document",
                        on_click=self._on_upload_click,
                    ),
                    collapse_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=16, right=8, top=12, bottom=12),
            bgcolor=COLORS["bg_obsidian"],
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border_hairline"])),
        )

        # Upload zone (shown when vault is empty)
        self.upload_zone = UploadZone(on_upload_click=self._on_upload_click)

        # Document list (shown when vault has documents)
        self.document_list = ft.ListView(
            expand=True,
            spacing=0,
            padding=0,
        )

        # Toast container (stacked toasts)
        self.toast_container = ft.Column(
            [],
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )

        # Stack toasts on top of content
        self.toast_stack = ft.Stack(
            [
                ft.Container(expand=True),  # Spacer
                ft.Container(
                    content=self.toast_container,
                    alignment=ft.Alignment(1, 1),
                    padding=ft.Padding(left=16, top=16, right=16, bottom=64),
                ),
            ],
            expand=True,
        )

        self.file_picker = ft.FilePicker()

        self.controls = [
            self.header,
            ft.Stack(
                [
                    ft.Container(
                        content=self.upload_zone,
                        expand=True,
                    ),
                    self.toast_stack,
                ],
                expand=True,
            ),
        ]

    def did_mount(self) -> None:
        """Called when the control is added to the page."""
        # Register FilePicker as a page service (required in Flet 0.85.x)
        self._page.services.append(self.file_picker)
        
        # Set up state observers for reactive updates
        app_state.add_observer("documents_changed", self._load_documents)
        app_state.add_observer("active_documents_changed", self._load_documents)
        self._load_documents()

    def _load_documents(self) -> None:
        """Load existing documents from vault."""
        try:
            documents = self.vault_manager.get_all_documents()
            if documents:
                self._show_document_list(documents)
            else:
                self._show_upload_zone()
        except Exception:
            logger.error("Failed to load documents", exc_info=True)
            self._show_error("Failed to load documents from vault")

    def _show_upload_zone(self) -> None:
        """Show upload zone (empty state)."""
        self.controls = [
            self.header,
            ft.Stack(
                [
                    ft.Container(
                        content=self.upload_zone,
                        expand=True,
                    ),
                    self.toast_stack,
                ],
                expand=True,
            ),
        ]
        self.update()

    def _show_document_list(self, documents: list[Any]) -> None:
        """Show document list with isolated click zones."""
        list_items: list[ft.Control] = []

        for doc in documents:
            icon_name = ft.Icons.PICTURE_AS_PDF if doc.file_type == "pdf" else ft.Icons.DESCRIPTION

            # ZONE 1: The Toggle Area (Left Side)
            toggle_area = ft.Container(
                content=ft.Row([
                    ft.Icon(icon_name, color=COLORS["text_secondary"], size=24),
                    ft.Container(width=12),
                    ft.Column([
                        ft.Text(doc.filename, color=COLORS["text_primary"], size=TYPOGRAPHY["body"]["size"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{doc.word_count} words • {doc.token_count} tokens", color=COLORS["text_secondary"], size=TYPOGRAPHY["micro"]["size"]),
                    ], spacing=4, expand=True),
                ]),
                expand=True,
                # Clicking anywhere in this left zone toggles the document
                on_click=lambda e, d=doc: self._on_document_click(e, d),
            )

            # ZONE 2: The Delete Button (Right Side)
            delete_btn = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=COLORS["text_muted"],
                icon_size=20,
                tooltip="Delete Document",
                # Clicking this explicitly calls our simplified delete method
                on_click=lambda e, d=doc: self._on_document_delete(e, d),
            )

            # Assemble the row
            row = ft.Container(
                content=ft.Row([
                    toggle_area,
                    ft.Row([
                        # Status Dot
                        ft.Container(
                            width=8, height=8, border_radius=4,
                            bgcolor=COLORS["accent_electric"] if doc.is_active else ft.Colors.TRANSPARENT,
                        ),
                        delete_btn
                    ], alignment=ft.MainAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.Padding(left=12, right=4, top=8, bottom=8),
                bgcolor=COLORS["bg_active"] if doc.is_active else COLORS["bg_obsidian"],
                data={"is_active": doc.is_active},  # Pass state to hover handler
                on_hover=self._on_document_hover,
            )
            list_items.append(row)

        # Update the UI efficiently
        self.document_list.controls = list_items
        self.controls = [
            self.header,
            ft.Stack(
                [
                    ft.Container(
                        content=self.document_list,
                        expand=True,
                    ),
                    self.toast_stack,
                ],
                expand=True,
            ),
        ]
        self.update()

    def _on_document_hover(self, e: Any) -> None:
        """Handle document row hover."""
        if not isinstance(e.control, ft.Container):
            return
        # Preserve active state background on hover out
        is_active = e.control.data.get("is_active", False) if e.control.data else False
        if e.data == "true":
            e.control.bgcolor = COLORS["bg_hover"]
        else:
            e.control.bgcolor = COLORS["bg_active"] if is_active else COLORS["bg_obsidian"]
        e.control.update()

    def _on_document_click(self, e: Any, doc: Any) -> None:
        """Handle document click to toggle active state."""
        try:
            new_active = not doc.is_active
            self.vault_manager.toggle_active(doc.id, new_active)
            # Update AppState to notify observers
            app_state.toggle_document_active(doc.id)
            # Reload documents to update UI
            self._load_documents()
        except VaultError:
            logger.error("Failed to toggle document active state", exc_info=True)
            self._show_error("Failed to update document")

    def _on_document_delete(self, e: Any, doc: Any) -> None:
        """Handle document deletion with confirmation dialog."""

        def handle_confirm(ev: Any) -> None:
            # Close the dialog first
            dialog.open = False
            self._page.update()

            # Perform the deletion
            try:
                self.vault_manager.delete_document(doc.id)
                app_state.remove_document(doc.id)
                self._show_success(f"Deleted: {doc.filename}")
                self._load_documents()  # Refresh the UI
            except Exception as ex:
                logger.error(f"Failed to delete {doc.filename}", exc_info=True)
                self._show_error("Failed to delete document")

        def handle_cancel(ev: Any) -> None:
            # Just close the dialog, do nothing else
            dialog.open = False
            self._page.update()

        # Create the dialog on the fly
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Document"),
            content=ft.Text(
                f"Are you sure you want to delete '{doc.filename}'?",
                color=COLORS["text_primary"]
            ),
            actions=[
                ft.TextButton("Cancel", on_click=handle_cancel),
                ft.TextButton(
                    "Delete",
                    on_click=handle_confirm,
                    style=ft.ButtonStyle(color=COLORS["accent_error"])
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Add dialog to overlay and open it (Flet 0.85.x imperative API)
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    async def _on_upload_click(self, e: Any) -> None:
        """Handle upload button click."""
        files = await self.file_picker.pick_files(
            allowed_extensions=["pdf", "txt"],
            allow_multiple=False,
        )
        if files and files[0].path:
            file_path = Path(files[0].path)
            self._handle_upload(file_path)

    def _handle_upload(self, file_path: Path) -> None:
        """Handle file upload in a background thread to prevent UI blocking."""

        def upload_worker() -> None:
            """Perform upload in background thread."""
            try:
                # Show loading state
                self._show_info("Uploading document...")

                # Upload document
                metadata = self.vault_manager.upload_document(file_path)

                # Update AppState to notify observers
                app_state.add_document({
                    "id": metadata.id,
                    "filename": metadata.filename,
                    "original_path": metadata.original_path,
                    "storage_path": metadata.storage_path,
                    "file_type": metadata.file_type,
                    "file_size_bytes": metadata.file_size_bytes,
                    "word_count": metadata.word_count,
                    "token_count": metadata.token_count,
                    "extracted_text": metadata.extracted_text,
                    "is_active": metadata.is_active,
                    "created_at": metadata.created_at,
                })

                # Show success
                self._show_success(f"Uploaded: {file_path.name}")

            except UnsupportedFileTypeError as e:
                self._show_error(e.message)
            except FileSizeExceededError as e:
                self._show_error(e.message)
            except VaultError as e:
                logger.error("Vault error during upload", exc_info=True)
                self._show_error(e.message)
            except Exception:
                logger.error("Unexpected error during upload", exc_info=True)
                self._show_error("Failed to upload document")

        # Run in background to avoid blocking UI
        self._page.run_thread(upload_worker)

    def _show_toast(self, toast: ToastNotification) -> None:
        """Show a toast notification."""
        toast.on_dismiss = lambda: self._remove_toast(toast)
        self.toasts.append(toast)
        self.toast_container.controls.append(toast)
        self.toast_container.update()

        # Schedule auto-dismiss using async task (UI-thread safe)
        async def auto_dismiss() -> None:
            await asyncio.sleep(4)
            self._remove_toast(toast)

        self._page.run_task(auto_dismiss)

    def _remove_toast(self, toast: ToastNotification) -> None:
        """Remove a toast notification."""
        if toast in self.toasts:
            self.toasts.remove(toast)
        if toast in self.toast_container.controls:
            self.toast_container.controls.remove(toast)
            self.toast_container.update()

    def _show_success(self, message: str) -> None:
        """Show success toast."""
        toast = ToastNotification(message, notification_type="success")
        self._show_toast(toast)

    def _show_error(self, message: str) -> None:
        """Show error toast."""
        toast = ToastNotification(message, notification_type="error")
        self._show_toast(toast)

    def _show_info(self, message: str) -> None:
        """Show info toast."""
        toast = ToastNotification(message, notification_type="info")
        self._show_toast(toast)
