"""Sources Vault panel component with document upload and list."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import flet as ft

from aria.document.vault import VaultManager
from aria.exceptions import FileSizeExceededError, UnsupportedFileTypeError, VaultError
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
        """Show document list with items."""
        list_items: list[ft.Control] = []
        for doc in documents:
            # Determine icon based on file type
            icon_name = ft.Icons.PICTURE_AS_PDF if doc.file_type == "pdf" else ft.Icons.DESCRIPTION

            # Create document row
            row = ft.Container(
                content=ft.Row(
                    [
                        # Left side: click area for toggle-active
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        icon=icon_name,
                                        color=COLORS["text_secondary"],
                                        size=24,
                                    ),
                                    ft.Container(width=12),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                doc.filename,
                                                color=COLORS["text_primary"],
                                                size=TYPOGRAPHY["body"]["size"],
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                f"{doc.word_count} words • {doc.token_count} tokens",
                                                color=COLORS["text_secondary"],
                                                size=TYPOGRAPHY["micro"]["size"],
                                            ),
                                        ],
                                        spacing=4,
                                        expand=True,
                                    ),
                                ],
                            ),
                            expand=True,
                            on_click=lambda e, d=doc: self._on_document_click(e, d),
                        ),
                        # Right side: status dot + delete button (isolated from toggle click)
                        ft.Row(
                            [
                                ft.Container(
                                    width=8,
                                    height=8,
                                    bgcolor=(
                                        COLORS["accent_electric"]
                                        if doc.is_active
                                        else COLORS["border_hairline"]
                                    ),
                                    border_radius=4,
                                    visible=doc.is_active,
                                ),
                                ft.Container(
                                    content=ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=COLORS["text_muted"],
                                        icon_size=20,
                                        tooltip="Delete Document",
                                        on_click=lambda e, d=doc: self._on_document_delete(e, d),
                                    ),
                                    padding=ft.Padding(left=4, right=4, top=4, bottom=4),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(left=12, right=4, top=8, bottom=8),
                bgcolor=COLORS["bg_active"] if doc.is_active else COLORS["bg_obsidian"],
                border=ft.Border(
                    left=(
                        ft.BorderSide(3, COLORS["accent_electric"])
                        if doc.is_active
                        else ft.BorderSide(0, ft.Colors.TRANSPARENT)
                    ),
                    bottom=ft.BorderSide(1, COLORS["border_hairline"]),
                ),
                on_hover=self._on_document_hover,
            )
            list_items.append(row)

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
        if e.data == "true":
            e.control.bgcolor = COLORS["bg_hover"]
        else:
            e.control.bgcolor = COLORS["bg_obsidian"]
        e.control.update()

    def _on_document_click(self, e: Any, doc: Any) -> None:
        """Handle document click to toggle active state."""

        def toggle_worker() -> None:
            try:
                new_active = not doc.is_active
                self.vault_manager.toggle_active(doc.id, new_active)
                self._load_documents()
            except VaultError:
                logger.error("Failed to toggle document active state", exc_info=True)
                self._show_error("Failed to update document")

        self._page.run_thread(toggle_worker)

    def _on_document_delete(self, e: Any, doc: Any) -> None:
        """Delete a document from the vault."""
        logger.info("Delete button clicked", extra={"doc_id": doc.id, "filename": doc.filename})

        def delete_worker() -> None:
            try:
                logger.info("Starting document deletion", extra={"doc_id": doc.id})
                self.vault_manager.delete_document(doc.id)
                self._load_documents()
                self._show_success(f"Deleted: {doc.filename}")
                logger.info("Document deleted successfully", extra={"doc_id": doc.id})
            except Exception:
                logger.error("Failed to delete document", exc_info=True, extra={"doc_id": doc.id})
                self._show_error("Failed to delete document")

        self._page.run_thread(delete_worker)

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
                self.vault_manager.upload_document(file_path)

                # Show success and reload
                self._show_success(f"Uploaded: {file_path.name}")
                self._load_documents()

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

        # Define a task to run after delay
        def auto_dismiss() -> None:
            import time
            time.sleep(4)
            self._remove_toast(toast)

        self._page.run_thread(auto_dismiss)

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
