import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from detector import (  # noqa: E402
    LogEntry,
    parse_line,
    load_log,
    detect_brute_force,
    detect_credential_stuffing,
)

SAMPLE_LOG = os.path.join(os.path.dirname(__file__), "..", "samples", "auth.log")


def entry(ts, ip, user, event):
    return LogEntry(datetime.fromisoformat(ts).replace(tzinfo=timezone.utc), ip, user, event)


class TestParseLine(unittest.TestCase):
    def test_parses_well_formed_line(self):
        e = parse_line("2026-09-24T10:15:03Z ip=203.0.113.5 user=admin event=failure")
        self.assertEqual(e.ip, "203.0.113.5")
        self.assertEqual(e.user, "admin")
        self.assertEqual(e.event, "failure")

    def test_skips_blank_and_comment_lines(self):
        self.assertIsNone(parse_line(""))
        self.assertIsNone(parse_line("   "))
        self.assertIsNone(parse_line("# a comment"))

    def test_skips_malformed_lines(self):
        self.assertIsNone(parse_line("not a valid log line"))
        self.assertIsNone(parse_line("2026-09-24T10:15:03Z ip=203.0.113.5 user=admin"))
        self.assertIsNone(parse_line("2026-09-24T10:15:03Z ip=203.0.113.5 user=admin event=maybe"))
        self.assertIsNone(parse_line("not-a-timestamp ip=1.2.3.4 user=a event=success"))


class TestLoadLog(unittest.TestCase):
    def test_loads_sample_log_sorted(self):
        entries = load_log(SAMPLE_LOG)
        self.assertGreater(len(entries), 0)
        timestamps = [e.timestamp for e in entries]
        self.assertEqual(timestamps, sorted(timestamps))


class TestBruteForce(unittest.TestCase):
    def test_flags_burst_within_window(self):
        entries = [
            entry("2026-01-01T00:00:00", "9.9.9.9", "admin", "failure"),
            entry("2026-01-01T00:00:05", "9.9.9.9", "admin", "failure"),
            entry("2026-01-01T00:00:10", "9.9.9.9", "admin", "failure"),
            entry("2026-01-01T00:00:15", "9.9.9.9", "admin", "failure"),
            entry("2026-01-01T00:00:20", "9.9.9.9", "admin", "failure"),
        ]
        findings = detect_brute_force(entries, window_seconds=60, threshold=5)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["ip"], "9.9.9.9")
        self.assertEqual(findings[0]["count"], 5)

    def test_ignores_failures_spread_outside_window(self):
        entries = [
            entry("2026-01-01T00:00:00", "9.9.9.9", "admin", "failure"),
            entry("2026-01-01T00:05:00", "9.9.9.9", "admin", "failure"),
            entry("2026-01-01T00:10:00", "9.9.9.9", "admin", "failure"),
        ]
        findings = detect_brute_force(entries, window_seconds=60, threshold=3)
        self.assertEqual(findings, [])

    def test_ignores_successes(self):
        entries = [entry("2026-01-01T00:00:00", "9.9.9.9", "admin", "success")] * 10
        findings = detect_brute_force(entries, window_seconds=60, threshold=5)
        self.assertEqual(findings, [])

    def test_sample_log_flags_admin_burst(self):
        entries = load_log(SAMPLE_LOG)
        findings = detect_brute_force(entries, window_seconds=60, threshold=5)
        self.assertTrue(any(f["ip"] == "203.0.113.5" for f in findings))


class TestCredentialStuffing(unittest.TestCase):
    def test_flags_spray_across_distinct_users(self):
        entries = [
            entry("2026-01-01T00:00:00", "9.9.9.9", "alice", "failure"),
            entry("2026-01-01T00:00:05", "9.9.9.9", "bob", "failure"),
            entry("2026-01-01T00:00:10", "9.9.9.9", "carol", "failure"),
            entry("2026-01-01T00:00:15", "9.9.9.9", "dave", "failure"),
            entry("2026-01-01T00:00:20", "9.9.9.9", "erin", "failure"),
        ]
        findings = detect_credential_stuffing(entries, window_seconds=60, distinct_users_threshold=5)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["users_targeted"], ["alice", "bob", "carol", "dave", "erin"])

    def test_does_not_flag_repeated_single_user(self):
        # Same user failing repeatedly is brute-force, not credential stuffing.
        entries = [entry("2026-01-01T00:00:00", "9.9.9.9", "admin", "failure")] * 10
        findings = detect_credential_stuffing(entries, window_seconds=60, distinct_users_threshold=5)
        self.assertEqual(findings, [])

    def test_sample_log_flags_spray_ip(self):
        entries = load_log(SAMPLE_LOG)
        findings = detect_credential_stuffing(entries, window_seconds=60, distinct_users_threshold=5)
        self.assertTrue(any(f["ip"] == "203.0.113.77" for f in findings))


if __name__ == "__main__":
    unittest.main()
