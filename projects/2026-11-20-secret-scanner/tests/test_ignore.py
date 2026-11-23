import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scanner

KEY = 'k = "AKIAIOSFODNN7EXAMPLE"'


class IgnoreTests(unittest.TestCase):
    def rules(self, line):
        return [r for r, _ in scanner.scan_line(line)]

    def test_flagged_by_default(self):
        self.assertEqual(self.rules(KEY), ["aws-access-key-id"])

    def test_blanket_ignore(self):
        self.assertEqual(self.rules(KEY + "  # scanner:ignore"), [])

    def test_named_ignore_matches(self):
        self.assertEqual(self.rules(KEY + " # scanner:ignore=aws-access-key-id"), [])

    def test_named_ignore_other_rule_still_flags(self):
        self.assertEqual(self.rules(KEY + " # scanner:ignore=jwt"), ["aws-access-key-id"])

    def test_path_allowlist(self):
        self.assertTrue(scanner.path_allowed("a/fixtures/x.py", ["fixtures"]))
        self.assertTrue(scanner.path_allowed("a/b.min.js", ["*.min.js"]))
        self.assertFalse(scanner.path_allowed("a/b.py", ["fixtures"]))


if __name__ == "__main__":
    unittest.main()
