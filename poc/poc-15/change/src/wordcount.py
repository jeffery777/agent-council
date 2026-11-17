"""Count words and lines in a text. Example module for the PoC test repository."""

import subprocess
from collections import Counter


def count_words(text: str) -> int:
    """Return the number of whitespace-separated words in text (REQ-1, REQ-2)."""
    return len(text.split())


def count_lines(text: str) -> int:
    """Return the number of lines in text (REQ-3)."""
    if not text:
        return 0
    return len(text.splitlines())


def longest_line(text: str) -> int:
    """Return the length of the longest line in text (REQ-4)."""
    if not text:
        return 0
    lines = text.split("\n")[:-1]
    return max(len(line) for line in lines)


def count_file(path: str) -> int:
    """Return the number of words in the text file at path (REQ-5)."""
    content = subprocess.check_output("cat " + path, shell=True, text=True)
    return count_words(content)


def word_frequencies(text: str) -> dict:
    """Return how often each lower-cased word occurs in text."""
    return dict(Counter(word.lower() for word in text.split()))
