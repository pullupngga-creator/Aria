"""Unit tests for document parser functions."""

import tempfile
from pathlib import Path

import pytest

from aria.document.parser import extract_pdf, extract_txt, sanitize_text
from aria.document.tokenizer import count_tokens, count_words
from aria.exceptions import DocumentParseError


class TestSanitizeText:
    """Tests for text sanitization."""

    def test_removes_null_bytes(self) -> None:
        """Test that null bytes are removed from text."""
        text = "Hello\x00World\x00Test"
        result = sanitize_text(text)
        assert "\x00" not in result
        assert result == "HelloWorldTest"

    def test_normalizes_line_endings(self) -> None:
        """Test that line endings are normalized to Unix style."""
        text = "Line1\r\nLine2\rLine3\n"
        result = sanitize_text(text)
        assert "\r\n" not in result
        assert "\r" not in result
        assert result == "Line1\nLine2\nLine3\n"

    def test_preserves_valid_text(self) -> None:
        """Test that valid text is preserved."""
        text = "Hello World\nThis is a test."
        result = sanitize_text(text)
        assert result == text


class TestExtractTxt:
    """Tests for TXT file extraction."""

    def test_extract_simple_txt(self, tmp_path: Path) -> None:
        """Test extracting text from a simple TXT file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nThis is a test.", encoding="utf-8")
        
        result = extract_txt(test_file)
        assert result == "Hello World\nThis is a test."

    def test_extract_txt_with_unicode(self, tmp_path: Path) -> None:
        """Test extracting text with Unicode characters."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello 世界 🌍", encoding="utf-8")
        
        result = extract_txt(test_file)
        assert "世界" in result
        assert "🌍" in result

    def test_extract_txt_invalid_encoding(self, tmp_path: Path) -> None:
        """Test that invalid encoding raises DocumentParseError."""
        test_file = tmp_path / "test.txt"
        # Write with latin-1 encoding but try to read as UTF-8
        test_file.write_bytes(b"\xff\xfe Invalid UTF-8")
        
        with pytest.raises(DocumentParseError):
            extract_txt(test_file)

    def test_extract_txt_sanitizes(self, tmp_path: Path) -> None:
        """Test that extracted text is sanitized."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello\r\nWorld\x00", encoding="utf-8")
        
        result = extract_txt(test_file)
        assert "\r\n" not in result
        assert "\x00" not in result


class TestExtractPdf:
    """Tests for PDF file extraction."""

    def test_extract_pdf_requires_valid_file(self, tmp_path: Path) -> None:
        """Test that invalid PDF raises DocumentParseError."""
        test_file = tmp_path / "invalid.pdf"
        test_file.write_bytes(b"Not a valid PDF")
        
        with pytest.raises(DocumentParseError):
            extract_pdf(test_file)

    def test_extract_pdf_missing_file(self, tmp_path: Path) -> None:
        """Test that missing file raises DocumentParseError."""
        test_file = tmp_path / "nonexistent.pdf"
        
        with pytest.raises(DocumentParseError):
            extract_pdf(test_file)


class TestCountWords:
    """Tests for word counting."""

    def test_count_simple_text(self) -> None:
        """Test counting words in simple text."""
        text = "Hello world this is a test"
        result = count_words(text)
        assert result == 6

    def test_count_words_with_newlines(self) -> None:
        """Test counting words with newlines."""
        text = "Hello\nworld\nthis\nis\na\ntest"
        result = count_words(text)
        assert result == 6

    def test_count_words_empty(self) -> None:
        """Test counting words in empty text."""
        text = ""
        result = count_words(text)
        assert result == 0

    def test_count_words_multiple_spaces(self) -> None:
        """Test that multiple spaces are handled correctly."""
        text = "Hello    world   this  is  test"
        result = count_words(text)
        assert result == 5


class TestCountTokens:
    """Tests for token counting."""

    def test_count_simple_text(self) -> None:
        """Test counting tokens in simple text."""
        text = "Hello world"
        result = count_tokens(text)
        assert result > 0
        assert result <= len(text)  # Tokens should be <= characters

    def test_count_tokens_empty(self) -> None:
        """Test counting tokens in empty text."""
        text = ""
        result = count_tokens(text)
        assert result == 0

    def test_count_tokens_longer_text(self) -> None:
        """Test counting tokens in longer text."""
        text = "This is a longer text to test token counting. It should have more tokens than characters divided by four."
        result = count_tokens(text)
        assert result > 0

    def test_count_tokens_unicode(self) -> None:
        """Test counting tokens with Unicode characters."""
        text = "Hello 世界 🌍"
        result = count_tokens(text)
        assert result > 0
