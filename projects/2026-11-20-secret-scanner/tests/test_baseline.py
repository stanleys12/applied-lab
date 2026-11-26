import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import baseline
import scanner

# Assembled at runtime so this file holds no token-shaped literal.
KEY_A = "AKIA" + "A" * 16
KEY_B = "AKIA" + "B" * 16
PEM = "-----BEGIN " + "PRIVATE KEY-----"


class BaselineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(tmp.cleanup)
        self.root = os.path.join(tmp.name, "src")
        os.mkdir(self.root)
        self.base = os.path.join(tmp.name, "baseline.json")  # outside the scanned root

    def put(self, *lines):
        with open(os.path.join(self.root, "a.py"), "w", encoding="utf-8") as fh:
            fh.write("".join(l + "\n" for l in lines))

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scanner.main([self.root] + list(args))
        return code, out.getvalue()

    def record(self, *lines):
        self.put(*lines)
        return self.run_cli("--write-baseline", self.base)

    def check(self, *lines):
        self.put(*lines)
        return self.run_cli("--baseline", self.base)

    def test_known_finding_survives_line_moves(self):
        self.assertEqual(self.record(KEY_A)[0], 0)
        code, out = self.check("# new header", "", KEY_A)
        self.assertEqual(code, 0)
        self.assertIn("1 suppressed", out)

    def test_new_secret_is_reported(self):
        self.record(KEY_A)
        code, out = self.check(KEY_A, KEY_B)
        self.assertEqual(code, 1)
        self.assertIn("a.py:2", out)
        self.assertNotIn("a.py:1", out)

    def test_extra_copy_is_reported(self):
        self.record(KEY_A)
        self.assertEqual(self.check(KEY_A, KEY_A)[0], 1)

    def test_stale_entries_are_mentioned(self):
        self.record(KEY_A)
        code, out = self.check("clean")
        self.assertEqual(code, 0)
        self.assertIn("1 stale", out)

    def test_file_has_no_raw_secret(self):
        self.record(KEY_A)
        with open(self.base, encoding="utf-8") as fh:
            self.assertNotIn(KEY_A, fh.read())

    def test_private_key_is_never_suppressed(self):
        code, out = self.record(PEM)
        self.assertEqual(code, 1)
        self.assertIn("cannot be baselined", out)
        self.assertEqual(self.check(PEM)[0], 1)

    def test_diff_finding_matches_tree_baseline(self):
        self.record(KEY_A)
        diff = "+++ b/a.py\n@@ -0,0 +9 @@\n+%s\n" % KEY_A
        found = list(scanner.scan_diff(diff))
        new, suppressed, _ = baseline.apply(found, baseline.load(self.base))
        self.assertEqual((new, suppressed), ([], 1))

    def test_missing_or_corrupt_baseline_exits_2(self):
        self.put("clean")
        self.assertEqual(self.run_cli("--baseline", self.base)[0], 2)
        for bad in ("not json", "[]", '{"version": 1, "findings": [{"count": 1}]}'):
            with open(self.base, "w", encoding="utf-8") as fh:
                fh.write(bad)
            self.assertEqual(self.run_cli("--baseline", self.base)[0], 2, bad)

    def test_write_refused_in_diff_mode(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("--staged", "--write-baseline", self.base)
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
