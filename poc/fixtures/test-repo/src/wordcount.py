"""Count words and lines in a text. Example module for the PoC test repository."""


def count_words(text: str) -> int:
    """Return the number of whitespace-separated words in text (REQ-1, REQ-2)."""
    return len(text.split())


def count_lines(text: str) -> int:
    """Return the number of lines in text (REQ-3)."""
    if not text:
        return 0
    return len(text.splitlines())
