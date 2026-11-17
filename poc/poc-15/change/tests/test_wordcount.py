import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wordcount import (  # noqa: E402
    count_file,
    count_lines,
    count_words,
    longest_line,
    word_frequencies,
)


class WordCountTest(unittest.TestCase):
    def test_counts_words(self):
        self.assertEqual(count_words("one two  three\nfour"), 4)

    def test_empty_text_has_no_words(self):
        self.assertEqual(count_words(""), 0)
        self.assertEqual(count_words("  \n\t"), 0)

    def test_counts_lines(self):
        self.assertEqual(count_lines(""), 0)
        self.assertEqual(count_lines("a\nb\n"), 2)
        self.assertEqual(count_lines("a\nb"), 2)

    def test_longest_line(self):
        self.assertEqual(longest_line(""), 0)
        self.assertEqual(longest_line("ab\nabcd\n"), 4)

    def test_count_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("one two three\n")
        try:
            self.assertEqual(count_file(fh.name), 3)
        finally:
            os.unlink(fh.name)

    def test_word_frequencies(self):
        self.assertEqual(word_frequencies("a A b"), {"a": 2, "b": 1})


if __name__ == "__main__":
    unittest.main()
