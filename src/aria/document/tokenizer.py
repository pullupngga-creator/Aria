"""Token counting utilities for extracted text."""

import logging

import tiktoken

logger = logging.getLogger(__name__)

# Use cl100k_base encoding (OpenAI-compatible) as per TECH_STACK.md
_TOKENIZER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken cl100k_base encoding.
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Number of tokens
    """
    try:
        tokens = _TOKENIZER.encode(text)
        return len(tokens)
    except Exception:
        logger.error("Failed to count tokens", extra={"text_length": len(text)})
        # Fallback: approximate tokens as chars / 4
        return len(text) // 4


def count_words(text: str) -> int:
    """Count words in text (whitespace-split approximation).
    
    Args:
        text: Text to count words for
        
    Returns:
        Number of words
    """
    return len(text.split())
