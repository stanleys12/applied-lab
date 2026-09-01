#!/usr/bin/env python3
"""Unit tests for minisast: one fixture snippet per rule, plus suppression checks.

Run with: python3 -m unittest discover -s tests -v
(from the project directory, or `python3 tests/test_scanner.py`)
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scanner import scan_file  # noqa: E402


def rule_ids(findings):
    return [f.rule for f in findings]


class RuleFixtureTest(unittest.TestCase):
    """Each case is a snippet that should trigger exactly its named rule
    and no other rule."""

    def _scan(self, source: str):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(source)
            path = Path(tmp.name)
        try:
            return scan_file(path)
        finally:
            path.unlink()

    def assert_triggers(self, source: str, rule: str):
        findings = self._scan(source)
        self.assertIn(rule, rule_ids(findings), f"expected '{rule}' in {findings}")

    def assert_clean(self, source: str):
        findings = self._scan(source)
        self.assertEqual(findings, [], f"expected no findings, got {findings}")

    def test_hardcoded_secret(self):
        self.assert_triggers('api_key = "sk-fake-1234567890"\n', "hardcoded-secret")

    def test_hardcoded_secret_ignores_placeholder(self):
        self.assert_clean('api_key = "changeme"\n')

    def test_eval_exec(self):
        self.assert_triggers("eval('1 + 1')\n", "eval-exec")

    def test_shell_injection(self):
        self.assert_triggers(
            "import subprocess\nsubprocess.call('ls', shell=True)\n",
            "shell-injection",
        )

    def test_shell_false_is_clean(self):
        self.assert_clean(
            "import subprocess\nsubprocess.call(['ls'], shell=False)\n"
        )

    def test_weak_hash(self):
        self.assert_triggers("import hashlib\nhashlib.md5(b'x')\n", "weak-hash")

    def test_sql_injection(self):
        self.assert_triggers(
            "def f(cur, name):\n    cur.execute(f\"SELECT * FROM t WHERE n = '{name}'\")\n",
            "sql-injection",
        )

    def test_sql_parameterized_is_clean(self):
        self.assert_clean(
            "def f(cur, name):\n    cur.execute('SELECT * FROM t WHERE n = ?', (name,))\n"
        )

    def test_insecure_deserialization(self):
        self.assert_triggers("import pickle\npickle.loads(b'x')\n", "insecure-deserialization")

    def test_unsafe_yaml_load(self):
        self.assert_triggers("import yaml\nyaml.load('a: 1')\n", "unsafe-yaml-load")

    def test_yaml_safe_loader_is_clean(self):
        self.assert_clean(
            "import yaml\nyaml.load('a: 1', Loader=yaml.SafeLoader)\n"
        )

    def test_disabled_tls_verify(self):
        self.assert_triggers(
            "import requests\nrequests.get('https://x', verify=False)\n",
            "disabled-tls-verify",
        )

    def test_insecure_random(self):
        self.assert_triggers(
            "import random\nsession_token = random.choice('abc')\n",
            "insecure-random",
        )

    def test_random_for_non_secret_var_is_clean(self):
        self.assert_clean("import random\ndice_roll = random.randint(1, 6)\n")


class SuppressionTest(unittest.TestCase):
    def _scan(self, source: str):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(source)
            path = Path(tmp.name)
        try:
            return scan_file(path)
        finally:
            path.unlink()

    def test_ignore_specific_rule(self):
        findings = self._scan(
            "import hashlib\nhashlib.md5(b'x')  # minisast: ignore[weak-hash]\n"
        )
        self.assertEqual(findings, [])

    def test_ignore_all_rules_on_line(self):
        findings = self._scan("eval('1')  # minisast: ignore\n")
        self.assertEqual(findings, [])

    def test_ignore_does_not_suppress_other_lines(self):
        findings = self._scan(
            "import hashlib\n"
            "hashlib.md5(b'x')  # minisast: ignore[weak-hash]\n"
            "hashlib.sha1(b'y')\n"
        )
        self.assertEqual(rule_ids(findings), ["weak-hash"])


if __name__ == "__main__":
    unittest.main()
