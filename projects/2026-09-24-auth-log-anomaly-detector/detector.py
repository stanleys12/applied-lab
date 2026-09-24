#!/usr/bin/env python3
"""
auth-log-anomaly-detector

Reads a stream of authentication log lines and flags patterns worth a
human's attention: brute-force bursts (many failed logins from one IP
in a short window). Educational/defensive only.

Log line format (one event per line):
    <ISO8601 timestamp> ip=<ip> user=<user> event=success|failure

Example:
    2026-09-24T10:15:03Z ip=203.0.113.5 user=alice event=failure
"""
from __future__ import annotations

import argparse
import sys
from collections import namedtuple
from datetime import datetime, timedelta

LogEntry = namedtuple("LogEntry", ["timestamp", "ip", "user", "event"])

LINE_FIELDS = ("ip", "user", "event")


def parse_timestamp(raw: str) -> datetime:
    # datetime.fromisoformat() only accepts a trailing 'Z' since Python 3.11;
    # normalize so this works on older interpreters too.
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def parse_line(line: str) -> LogEntry | None:
    """Parse one log line into a LogEntry, or None if malformed/blank."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split()
    if len(parts) < 4:
        return None

    try:
        timestamp = parse_timestamp(parts[0])
    except ValueError:
        return None

    fields = {}
    for token in parts[1:]:
        if "=" not in token:
            return None
        key, _, value = token.partition("=")
        fields[key] = value

    if not all(f in fields for f in LINE_FIELDS):
        return None
    if fields["event"] not in ("success", "failure"):
        return None

    return LogEntry(timestamp, fields["ip"], fields["user"], fields["event"])


def load_log(path: str) -> list[LogEntry]:
    """Parse a log file, silently skipping malformed lines, sorted by time."""
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = parse_line(line)
            if entry is not None:
                entries.append(entry)
    entries.sort(key=lambda e: e.timestamp)
    return entries


def detect_brute_force(entries: list[LogEntry], window_seconds: int = 60, threshold: int = 5):
    """
    Flag IPs with >= threshold failed logins inside any window_seconds
    sliding window. Uses a two-pointer sweep over failures grouped by IP,
    so it's O(n) per IP rather than O(n^2).

    Returns a list of dicts, one per distinct burst found, sorted by
    window start time.
    """
    failures_by_ip: dict[str, list[LogEntry]] = {}
    for e in entries:
        if e.event == "failure":
            failures_by_ip.setdefault(e.ip, []).append(e)

    findings = []
    window = timedelta(seconds=window_seconds)

    for ip, fails in failures_by_ip.items():
        left = 0
        n = len(fails)
        for right in range(n):
            while fails[right].timestamp - fails[left].timestamp > window:
                left += 1
            count = right - left + 1
            if count >= threshold:
                burst = fails[left:right + 1]
                findings.append({
                    "rule": "brute-force",
                    "ip": ip,
                    "window_start": burst[0].timestamp,
                    "window_end": burst[-1].timestamp,
                    "count": count,
                    "users_targeted": sorted({e.user for e in burst}),
                })
                # Skip past this burst so one flood doesn't emit a finding
                # for every single trailing event inside it.
                left = right + 1

    findings.sort(key=lambda f: f["window_start"])
    return findings


def format_finding(f: dict) -> str:
    users = ", ".join(f["users_targeted"])
    return (
        f"[{f['rule']}] {f['window_start'].isoformat()} - {f['window_end'].isoformat()} "
        f"ip={f['ip']} count={f['count']} users=[{users}]"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Detect anomalies in auth logs.")
    parser.add_argument("logfile", help="path to the auth log")
    parser.add_argument("--window", type=int, default=60, help="brute-force window in seconds (default: 60)")
    parser.add_argument("--threshold", type=int, default=5, help="failures within window to flag (default: 5)")
    args = parser.parse_args(argv)

    entries = load_log(args.logfile)
    findings = detect_brute_force(entries, window_seconds=args.window, threshold=args.threshold)

    for f in findings:
        print(format_finding(f))

    print(f"\n{len(entries)} event(s) parsed, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
