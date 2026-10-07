#!/usr/bin/env python3
"""`luce fmt` keeps each comment with the code it describes (§17.6): a comment right above a
statement or a declaration stays right above it, a blank line the source put above a comment
block stays above it, a comment after code stays after that line, and one after a block's last
statement, as deep as it, stays in the block. Formatting the canonical text changes nothing."""
from pathlib import Path
import subprocess
import tempfile
import unittest

LUCE = Path(__file__).resolve().parents[1] / "build/luce"

CANONICAL = """\
# right above the import
import math

# right above the constant
let limit = 3

# right above the function, after a blank line
func f(x: int) -> int:
    let a = x  # after a binding
    # right above a binding
    let b = a
    # right above an assignment
    _ = g(b)
    # right above a call
    g(a)  # after a call
    # The Application first: a comment block
    # of two lines.

    # After a blank line: a block of two lines
    # right above the statement it describes.
    let c = a + b
    if c > 0:
        return c
        # ends the `if` block
    # right above the return
    return b
    # ends the function

class C:
    var n: int

    # right above a method
    func get(self) -> int:
        return self.n

# the module's last comment
"""


class Comments(unittest.TestCase):
    def fmt(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.luc"
            path.write_text(text)
            return subprocess.run([str(LUCE), "fmt", str(path)], capture_output=True, text=True, check=True).stdout

    def test_comments_stay_attached(self):
        self.assertEqual(self.fmt(CANONICAL), CANONICAL)

    def test_blank_line_stays_above_a_comment_block(self):
        source = "func f() -> int:\n    let a = 1\n\n    # two lines about\n    # the return\n    return a\n"
        self.assertEqual(self.fmt(source), source)

    def test_blank_line_between_comment_and_statement_is_kept(self):
        source = "func f() -> int:\n    let a = 1\n    # a note\n\n    return a\n"
        self.assertEqual(self.fmt(source), source)

    def test_blank_lines_collapse_to_one(self):
        source = "func f() -> int:\n    let a = 1\n\n\n    # a note\n    return a\n"
        self.assertEqual(self.fmt(source), "func f() -> int:\n    let a = 1\n\n    # a note\n    return a\n")

    def test_idempotent(self):
        once = self.fmt(CANONICAL)
        self.assertEqual(self.fmt(once), once)


if __name__ == "__main__":
    unittest.main()
