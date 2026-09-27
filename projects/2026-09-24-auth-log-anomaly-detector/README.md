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
[CRITICAL] [anomalous-success] 2026-09-24T10:14:58+00:00 - 2026-09-24T10:15:41+00:00 ip=203.0.113.5 count=7 users=[admin]
[HIGH    ] [credential-stuffing] 2026-09-24T14:10:05+00:00 - 2026-09-24T14:10:29+00:00 ip=203.0.113.77 count=5 users=[alice, bob, carol, dave, erin]
[MEDIUM  ] [brute-force] 2026-09-24T10:14:58+00:00 - 2026-09-24T10:15:22+00:00 ip=203.0.113.5 count=5 users=[admin]
[MEDIUM  ] [brute-force] 2026-09-24T14:10:05+00:00 - 2026-09-24T14:10:29+00:00 ip=203.0.113.77 count=5 users=[alice, bob, carol, dave, erin]

23 event(s) parsed, 4 finding(s) (critical=1, high=1, medium=2)
```

Findings are sorted worst-severity-first (`critical` > `high` > `medium`).
Use `--min-severity` to cut the noise, e.g. only see things that actually
got past the front door:

```bash
python3 detector.py samples/auth.log --min-severity high
```

Tune the thresholds:

```bash
python3 detector.py samples/auth.log --window 30 --threshold 8 --stuffing-threshold 3 --success-threshold 4
```

For feeding findings into other tooling, use `--format json` or
`--format csv` instead of the human-readable default:

```bash
python3 detector.py samples/auth.log --format json
python3 detector.py samples/auth.log --format csv
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
- **anomalous-success** — a successful login for a given ip+user
  immediately following >= N failed logins for that *same* ip+user
  within a sliding window (default: 3 within 60s) — the "attacker
  eventually guessed right" case. Grouped by (ip, user) rather than
  by ip alone, so an unrelated user succeeding from a noisy IP never
  gets tainted by someone else's failure burst.

All three rules are implemented as an O(n) two-pointer sweep per
group rather than a naive O(n²) scan.

Each rule has a fixed severity (`anomalous-success` = critical,
`credential-stuffing` = high, `brute-force` = medium), findings are
reported worst-first, and the summary line breaks the count down by
severity. Output can be rendered as human-readable text (default),
JSON, or CSV via `--format`.

## Status

Done. All three planned detection rules, severity-ranked reporting,
and machine-readable output are implemented and tested.
