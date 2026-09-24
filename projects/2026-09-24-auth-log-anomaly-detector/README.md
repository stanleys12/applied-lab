# auth-log-anomaly-detector

A small, from-scratch log-anomaly detector for authentication events.
Parses a stream of login attempts and flags patterns that deserve a
human's attention: brute-force bursts (many failed logins from one
source in a short window) and credential-stuffing sprays (one source
failing logins across many distinct accounts). Educational/defensive
only: it surfaces suspicious patterns in logs you already own, it does
not attack anything.

## Why

Real SIEM rule engines are black boxes. This project builds the
detection logic in the open — sliding-window statistics over plain
Python data structures — so each rule's assumptions and blind spots
are visible and easy to extend.

## Log format

One event per line:

```
<ISO8601 timestamp> ip=<ip> user=<user> event=success|failure
```

```
2026-09-24T10:15:03Z ip=203.0.113.5 user=admin event=failure
```

## Run it

```bash
python3 detector.py samples/auth.log
```

Sample output against `samples/auth.log` (normal daily traffic plus an
embedded brute-force burst against `admin` and a credential-stuffing
spray across five accounts):

```
[brute-force] 2026-09-24T10:14:58+00:00 - 2026-09-24T10:15:22+00:00 ip=203.0.113.5 count=5 users=[admin]
[brute-force] 2026-09-24T14:10:05+00:00 - 2026-09-24T14:10:29+00:00 ip=203.0.113.77 count=5 users=[alice, bob, carol, dave, erin]
[credential-stuffing] 2026-09-24T14:10:05+00:00 - 2026-09-24T14:10:29+00:00 ip=203.0.113.77 count=5 users=[alice, bob, carol, dave, erin]

23 event(s) parsed, 3 finding(s)
```

Tune the thresholds:

```bash
python3 detector.py samples/auth.log --window 30 --threshold 8 --stuffing-threshold 3
```

Exit code is `1` if any finding is present (so it can gate CI), `0` otherwise.

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

## Rules implemented so far

- **brute-force** — >= N failed logins from the same IP within a
  sliding time window (default: 5 within 60s).
- **credential-stuffing** — failed logins from the same IP spread
  across >= N distinct usernames within a sliding time window
  (default: 5 within 60s) — catches account-spraying that a per-user
  threshold would miss, even when it also trips brute-force by volume.

Both rules are implemented as an O(n) two-pointer sweep per IP rather
than a naive O(n²) scan.

## Roadmap

- per-user anomalous-success detection (success immediately following
  a failure burst, e.g. the attacker above eventually got in)
- summary/report mode with severity levels
- CSV/JSON output for feeding into other tooling
