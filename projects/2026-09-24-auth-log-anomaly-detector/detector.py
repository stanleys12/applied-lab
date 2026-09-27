#!/usr/bin/env python3
"""
auth-log-anomaly-detector

Reads a stream of authentication log lines and flags patterns worth a
human's attention: brute-force bursts (many failed logins from one IP
in a short window) and credential-stuffing sprays (those failures
spread across many distinct accounts rather than hammering one).
Educational/defensive only.

Log line format (one event per line):
    <ISO8601 timestamp> ip=<ip> user=<user> event=success|failure

Example:
    2026-09-24T10:15:03Z ip=203.0.113.5 user=alice event=failure
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import namedtuple
from datetime import datetime, timedelta

LogEntry = namedtuple("LogEntry", ["timestamp", "ip", "user", "event"])

LINE_FIELDS = ("ip", "user", "event")

# Static per-rule severity: anomalous-success means someone likely *got in*,
# which is worse than a spray/burst that may still have been repelled.
SEVERITY = {
    "anomalous-success": "critical",
    "credential-stuffing": "high",
    "brute-force": "medium",
}
SEVERITY_ORDER = ("critical", "high", "medium", "low")


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
                    "severity": SEVERITY["brute-force"],
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


def detect_credential_stuffing(entries: list[LogEntry], window_seconds: int = 60, distinct_users_threshold: int = 5):
    """
    Flag IPs whose failed logins target >= distinct_users_threshold distinct
    usernames inside any window_seconds sliding window. This is the
    credential-stuffing / username-enumeration counterpart to
    detect_brute_force: that rule catches one IP hammering *one* account,
    this one catches an IP spraying attempts across *many* accounts, which
    a per-account threshold would miss entirely.

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
        user_counts: dict[str, int] = {}
        n = len(fails)
        for right in range(n):
            user_counts[fails[right].user] = user_counts.get(fails[right].user, 0) + 1
            while fails[right].timestamp - fails[left].timestamp > window:
                left_user = fails[left].user
                user_counts[left_user] -= 1
                if user_counts[left_user] == 0:
                    del user_counts[left_user]
                left += 1

            if len(user_counts) >= distinct_users_threshold:
                burst = fails[left:right + 1]
                findings.append({
                    "rule": "credential-stuffing",
                    "severity": SEVERITY["credential-stuffing"],
                    "ip": ip,
                    "window_start": burst[0].timestamp,
                    "window_end": burst[-1].timestamp,
                    "count": len(burst),
                    "users_targeted": sorted(user_counts),
                })
                # Reset so one long spray emits one finding, not one per
                # trailing event inside it.
                left = right + 1
                user_counts = {}

    findings.sort(key=lambda f: f["window_start"])
    return findings


def detect_anomalous_success(entries: list[LogEntry], window_seconds: int = 60, threshold: int = 3):
    """
    Flag a successful login that immediately follows >= threshold failed
    logins for the *same* ip+user pair within window_seconds — i.e. someone
    hammered a specific account with failures and then got in. Grouping by
    (ip, user) rather than by ip alone (like detect_brute_force) means this
    catches the "attacker eventually guessed right" case without also
    tripping on an unrelated user who happens to succeed from a noisy IP.

    Returns a list of dicts, one per anomalous success, sorted by time.
    """
    by_pair: dict[tuple[str, str], list[LogEntry]] = {}
    for e in entries:
        by_pair.setdefault((e.ip, e.user), []).append(e)

    findings = []
    window = timedelta(seconds=window_seconds)

    for (ip, user), events in by_pair.items():
        left = 0
        fail_count = 0
        for right in range(len(events)):
            if events[right].event == "failure":
                fail_count += 1
            while events[right].timestamp - events[left].timestamp > window:
                if events[left].event == "failure":
                    fail_count -= 1
                left += 1
            if events[right].event == "success" and fail_count >= threshold:
                findings.append({
                    "rule": "anomalous-success",
                    "severity": SEVERITY["anomalous-success"],
                    "ip": ip,
                    "window_start": events[left].timestamp,
                    "window_end": events[right].timestamp,
                    "count": fail_count,
                    "users_targeted": [user],
                })
                # Require a fresh burst before flagging again for this pair.
                left = right + 1
                fail_count = 0

    findings.sort(key=lambda f: f["window_start"])
    return findings


def format_finding(f: dict) -> str:
    users = ", ".join(f["users_targeted"])
    return (
        f"[{f['severity'].upper():<8}] [{f['rule']}] {f['window_start'].isoformat()} - "
        f"{f['window_end'].isoformat()} ip={f['ip']} count={f['count']} users=[{users}]"
    )


CSV_FIELDS = ("severity", "rule", "window_start", "window_end", "ip", "count", "users_targeted")


def findings_to_json(findings: list[dict]) -> str:
    """Serialize findings to a JSON array, with timestamps as ISO 8601 strings."""
    serializable = []
    for f in findings:
        row = dict(f)
        row["window_start"] = f["window_start"].isoformat()
        row["window_end"] = f["window_end"].isoformat()
        serializable.append(row)
    return json.dumps(serializable, indent=2)


def findings_to_csv(findings: list[dict]) -> str:
    """Serialize findings to CSV text (one row per finding, users semicolon-joined)."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for f in findings:
        writer.writerow({
            "severity": f["severity"],
            "rule": f["rule"],
            "window_start": f["window_start"].isoformat(),
            "window_end": f["window_end"].isoformat(),
            "ip": f["ip"],
            "count": f["count"],
            "users_targeted": ";".join(f["users_targeted"]),
        })
    return out.getvalue()


def summarize(findings: list[dict]) -> str:
    """One line per severity level present, ordered worst-first, plus a total."""
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for f in findings:
        counts[f["severity"]] += 1
    parts = [f"{sev}={counts[sev]}" for sev in SEVERITY_ORDER if counts[sev]]
    breakdown = f" ({', '.join(parts)})" if parts else ""
    return f"{len(findings)} finding(s){breakdown}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Detect anomalies in auth logs.")
    parser.add_argument("logfile", help="path to the auth log")
    parser.add_argument("--window", type=int, default=60, help="brute-force window in seconds (default: 60)")
    parser.add_argument("--threshold", type=int, default=5, help="failures within window to flag (default: 5)")
    parser.add_argument("--stuffing-window", type=int, default=60, help="credential-stuffing window in seconds (default: 60)")
    parser.add_argument("--stuffing-threshold", type=int, default=5, help="distinct usernames within window to flag (default: 5)")
    parser.add_argument("--success-window", type=int, default=60, help="anomalous-success window in seconds (default: 60)")
    parser.add_argument("--success-threshold", type=int, default=3, help="failures before a success to flag (default: 3)")
    parser.add_argument(
        "--min-severity", choices=SEVERITY_ORDER, default="low",
        help="only report findings at or above this severity (default: low, i.e. everything)",
    )
    parser.add_argument(
        "--format", choices=("text", "json", "csv"), default="text",
        help="output format: human-readable text, JSON array, or CSV (default: text)",
    )
    args = parser.parse_args(argv)

    entries = load_log(args.logfile)
    findings = detect_brute_force(entries, window_seconds=args.window, threshold=args.threshold)
    findings += detect_credential_stuffing(
        entries, window_seconds=args.stuffing_window, distinct_users_threshold=args.stuffing_threshold
    )
    findings += detect_anomalous_success(
        entries, window_seconds=args.success_window, threshold=args.success_threshold
    )

    min_rank = SEVERITY_ORDER.index(args.min_severity)
    findings = [f for f in findings if SEVERITY_ORDER.index(f["severity"]) <= min_rank]
    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["window_start"]))

    if args.format == "json":
        print(findings_to_json(findings))
    elif args.format == "csv":
        print(findings_to_csv(findings), end="")
    else:
        for f in findings:
            print(format_finding(f))
        print(f"\n{len(entries)} event(s) parsed, {summarize(findings)}")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
