"""Document text extraction parsers for PDF and TXT files."""

import logging
from pathlib import Path

import fitz  # type: ignore # pymupdf

from aria.exceptions import DocumentParseError

logger = logging.getLogger(__name__)


def sanitize_text(text: str) -> str:
    """Sanitize extracted text by removing null bytes and normalizing line endings.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Sanitized text with Unix line endings and no null bytes
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize line endings to Unix style
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def extract_pdf(file_path: Path) -> str:
    """Extract text from PDF file using pymupdf.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
        
    Raises:
        DocumentParseError: If PDF extraction fails
    """
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return sanitize_text(text)
    except fitz.FileDataError as e:
        logger.error("PDF file is corrupted or invalid", extra={"path": str(file_path)})
        raise DocumentParseError(f"PDF file is corrupted: {file_path}") from e
    except Exception as e:
        logger.error("Failed to extract text from PDF", extra={"path": str(file_path)})
        raise DocumentParseError(f"Failed to extract text from PDF: {file_path}") from e


def extract_txt(file_path: Path) -> str:
    """Extract text from plain text file.
    
    Args:
        file_path: Path to the TXT file
        
    Returns:
        Extracted text as a string
        
    Raises:
        DocumentParseError: If text extraction fails
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            text = f.read()
        return sanitize_text(text)
    except UnicodeDecodeError as e:
        logger.error("Failed to decode text file as UTF-8", extra={"path": str(file_path)})
        raise DocumentParseError(f"Text file encoding error: {file_path}") from e
    except Exception as e:
        logger.error("Failed to read text file", extra={"path": str(file_path)})
        raise DocumentParseError(f"Failed to read text file: {file_path}") from e
