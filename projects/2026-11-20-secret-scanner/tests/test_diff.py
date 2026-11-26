import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import gitdiff
import scanner

# Assembled at runtime so this file holds no token-shaped literal.
FAKE_KEY = "AKIA" + "IOSFODNN7EXAMPLE"

DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -3 +3,2 @@ def f():
-OLD = "{key}"
+x = 1
+KEY = "{key}"
@@ -10,0 +12 @@
+++ not a header, just content
\\ No newline at end of file
diff --git a/gone.py b/gone.py
--- a/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-KEY = "{key}"
diff --git a/fixtures/t.py b/fixtures/t.py
--- /dev/null
+++ b/fixtures/t.py
@@ -0,0 +1 @@
+KEY = "{key}"
""".format(key=FAKE_KEY)


class DiffTests(unittest.TestCase):
    def test_added_lines_and_numbers(self):
        got = [(p, n) for p, n, _ in gitdiff.added_lines(DIFF)]
        self.assertEqual(got, [("app.py", 3), ("app.py", 4), ("app.py", 12), ("fixtures/t.py", 1)])

    def test_header_lookalike_is_content(self):
        texts = [t for _, _, t in gitdiff.added_lines(DIFF)]
        self.assertIn("++ not a header, just content", texts)

    def test_context_lines_advance_numbering(self):
        diff = "+++ b/a\n@@ -1,3 +1,4 @@\n one\n two\n+new\n three\n"
        self.assertEqual(list(gitdiff.added_lines(diff)), [("a", 3, "new")])

    def test_removed_secrets_are_not_reported(self):
        found = list(scanner.scan_diff(DIFF, ["fixtures"]))
        self.assertEqual([(p, n, r) for p, n, r, _ in found], [("app.py", 4, "aws-access-key-id")])
        self.assertNotIn(FAKE_KEY, found[0][3])

    def test_unquote_path(self):
        self.assertEqual(gitdiff.unquote_path("b/my file.py\t"), "b/my file.py")
        self.assertEqual(gitdiff.unquote_path('"b/q\\"uote.py"'), 'b/q"uote.py')
        self.assertEqual(gitdiff.unquote_path('"b/caf\\303\\251\\t.py"'), "b/café\t.py")

    def test_option_like_revision_rejected(self):
        with self.assertRaises(RuntimeError):
            gitdiff.git_diff(HERE, rev="--output=x")

    def test_bad_revision_exits_2_not_clean(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(scanner.main([HERE, "--since", "no-such-rev-xyz"]), 2)

    def test_diff_file_mode(self):
        with tempfile.NamedTemporaryFile("w", suffix=".diff", dir=HERE, delete=False) as fh:
            fh.write(DIFF)
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(scanner.main([HERE, "--diff", fh.name]), 1)
            self.assertNotIn(FAKE_KEY, out.getvalue())
        finally:
            os.unlink(fh.name)


if __name__ == "__main__":
    unittest.main()
