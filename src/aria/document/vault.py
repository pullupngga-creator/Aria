"""Vault management for document storage and metadata."""

import logging
import uuid
from pathlib import Path
from typing import NamedTuple

from aria.db.connection import get_connection
from aria.document.parser import extract_pdf, extract_txt
from aria.document.tokenizer import count_tokens, count_words
from aria.exceptions import FileSizeExceededError, UnsupportedFileTypeError, VaultError

logger = logging.getLogger(__name__)

# Phase 0: Only PDF and TXT supported
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

# Vault storage directory
_VAULT_DIR: Path = Path.home() / ".local" / "share" / "aria" / "vault"


class DocumentMetadata(NamedTuple):
    """Metadata for a document in the vault."""

    id: str
    filename: str
    original_path: str
    storage_path: str
    file_type: str
    file_size_bytes: int
    word_count: int
    token_count: int
    extracted_text: str | None
    is_active: bool
    created_at: str


class VaultManager:
    """Manages document storage, parsing, and metadata persistence."""

    def __init__(self) -> None:
        """Initialize vault manager and ensure vault directory exists."""
        _VAULT_DIR.mkdir(parents=True, exist_ok=True)

    def validate_file(self, file_path: Path) -> None:
        """Validate file type and size before upload.
        
        Args:
            file_path: Path to the file to validate
            
        Raises:
            UnsupportedFileTypeError: If file type is not PDF or TXT
            FileSizeExceededError: If file exceeds 50MB limit
        """
        # Check file extension
        ext = file_path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {ext}. Only PDF and TXT are supported in Phase 0."
            )

        # Check file size
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            raise FileSizeExceededError(
                f"File size ({size_mb:.1f}MB) exceeds 50MB limit."
            )

    def upload_document(self, file_path: Path) -> DocumentMetadata:
        """Upload a document to the vault: validate, copy, parse, and store metadata.
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            DocumentMetadata with all extracted information
            
        Raises:
            UnsupportedFileTypeError: If file type is not supported
            FileSizeExceededError: If file exceeds size limit
            VaultError: If upload or database operations fail
        """
        try:
            # Validate file
            self.validate_file(file_path)

            # Generate unique storage path
            doc_id = str(uuid.uuid4())
            storage_filename = f"doc_{doc_id}.txt"
            storage_path = _VAULT_DIR / storage_filename

            # Extract text based on file type
            file_type = file_path.suffix.lower().lstrip(".")
            if file_type == "pdf":
                extracted_text = extract_pdf(file_path)
            else:  # txt
                extracted_text = extract_txt(file_path)

            # Store extracted text as UTF-8 .txt file
            storage_path.write_text(extracted_text, encoding="utf-8")

            # Calculate metadata
            word_count = count_words(extracted_text)
            token_count = count_tokens(extracted_text)
            file_size_bytes = file_path.stat().st_size
            extracted_text_preview = extracted_text[:500] if extracted_text else None

            # Insert into database
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO documents (
                    id, filename, original_path, storage_path, file_type,
                    file_size_bytes, word_count, token_count, extracted_text, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    file_path.name,
                    str(file_path),
                    str(storage_path),
                    file_type,
                    file_size_bytes,
                    word_count,
                    token_count,
                    extracted_text_preview,
                    0,  # is_active defaults to 0
                ),
            )
            conn.commit()

            # Update FTS index
            cursor.execute(
                "INSERT INTO documents_fts(rowid, filename, extracted_text) VALUES (?, ?, ?)",
                (cursor.lastrowid, file_path.name, extracted_text_preview or ""),
            )
            conn.commit()

            logger.info(
                "Document uploaded successfully",
                extra={
                    "doc_id": doc_id,
                    "doc_name": file_path.name,
                    "file_type": file_type,
                    "token_count": token_count,
                },
            )

            # Return metadata
            return DocumentMetadata(
                id=doc_id,
                filename=file_path.name,
                original_path=str(file_path),
                storage_path=str(storage_path),
                file_type=file_type,
                file_size_bytes=file_size_bytes,
                word_count=word_count,
                token_count=token_count,
                extracted_text=extracted_text_preview,
                is_active=False,
                created_at="",  # Will be populated by DB trigger
            )

        except (UnsupportedFileTypeError, FileSizeExceededError):
            raise
        except Exception as e:
            logger.error("Failed to upload document", extra={"path": str(file_path)})
            raise VaultError(f"Failed to upload document: {file_path}") from e

    def get_all_documents(self) -> list[DocumentMetadata]:
        """Retrieve all documents from the vault.
        
        Returns:
            List of DocumentMetadata for all documents
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, filename, original_path, storage_path, file_type,
                   file_size_bytes, word_count, token_count, extracted_text,
                   is_active, created_at
            FROM documents
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()
        return [
            DocumentMetadata(
                id=row["id"],
                filename=row["filename"],
                original_path=row["original_path"],
                storage_path=row["storage_path"],
                file_type=row["file_type"],
                file_size_bytes=row["file_size_bytes"],
                word_count=row["word_count"],
                token_count=row["token_count"],
                extracted_text=row["extracted_text"],
                is_active=bool(int(row["is_active"] or 0)),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_document(self, doc_id: str) -> DocumentMetadata | None:
        """Retrieve a single document by ID.
        
        Args:
            doc_id: UUID of the document
            
        Returns:
            DocumentMetadata if found, None otherwise
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, filename, original_path, storage_path, file_type,
                   file_size_bytes, word_count, token_count, extracted_text,
                   is_active, created_at
            FROM documents
            WHERE id = ?
            """,
            (doc_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return DocumentMetadata(
            id=row["id"],
            filename=row["filename"],
            original_path=row["original_path"],
            storage_path=row["storage_path"],
            file_type=row["file_type"],
            file_size_bytes=row["file_size_bytes"],
            word_count=row["word_count"],
            token_count=row["token_count"],
            extracted_text=row["extracted_text"],
            is_active=bool(int(row["is_active"] or 0)),
            created_at=row["created_at"],
        )

    def delete_document(self, doc_id: str) -> None:
        """Delete a document from the vault (database and file storage).
        
        Args:
            doc_id: UUID of the document to delete
            
        Raises:
            VaultError: If document not found or deletion fails
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Get storage path before deletion
            cursor.execute("SELECT storage_path FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row is None:
                raise VaultError(f"Document not found: {doc_id}")

            storage_path = Path(row["storage_path"])

            # Delete from database (CASCADE will handle FTS)
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()

            # Delete file from storage
            if storage_path.exists():
                storage_path.unlink()

            logger.info("Document deleted", extra={"doc_id": doc_id})

        except VaultError:
            raise
        except Exception as e:
            logger.error("Failed to delete document", extra={"doc_id": doc_id})
            raise VaultError(f"Failed to delete document: {doc_id}") from e

    def toggle_active(self, doc_id: str, is_active: bool) -> None:
        """Toggle a document's active state for context binding.
        
        Args:
            doc_id: UUID of the document
            is_active: New active state
            
        Raises:
            VaultError: If document not found or update fails
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, doc_id),
            )
            conn.commit()
            logger.info(
                "Document active state toggled",
                extra={"doc_id": doc_id, "is_active": is_active},
            )
        except Exception as e:
            logger.error("Failed to toggle document active state", extra={"doc_id": doc_id})
            raise VaultError(f"Failed to toggle document active state: {doc_id}") from e
