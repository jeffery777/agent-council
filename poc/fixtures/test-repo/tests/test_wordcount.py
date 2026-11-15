import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wordcount import count_lines, count_words  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
