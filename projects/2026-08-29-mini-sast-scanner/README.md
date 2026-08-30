# mini-sast-scanner

A small static-analysis tool that scans Python source for common security
smells: hardcoded credentials, `eval`/`exec`, `subprocess(shell=True)`,
weak hashes, and SQL built via string interpolation. Educational/defensive
only — it finds patterns worth a human's attention; it does not exploit
anything.

## Why

Full SAST tools (Semgrep, Bandit) are great but opaque. This project
builds the same idea from scratch — AST traversal plus a few regexes —
so each rule's logic and blind spots are visible and easy to extend.

## Run it

```bash
# scan a single file
python3 scanner.py samples/vulnerable.py

# scan a directory recursively (all *.py files)
python3 scanner.py .
```

Exit code is `1` if any HIGH-severity finding is present (so it can gate
CI), `0` otherwise.

Sample output against the intentionally-flawed fixture in `samples/`:

```
[HIGH] samples/vulnerable.py:7  hardcoded-secret: possible hardcoded credential in 'api_key'
[HIGH] samples/vulnerable.py:8  hardcoded-secret: possible hardcoded credential in 'db_password'
[HIGH] samples/vulnerable.py:12  shell-injection: subprocess.call(shell=True) risks command injection
[HIGH] samples/vulnerable.py:16  eval-exec: use of eval() can execute arbitrary code
[LOW ] samples/vulnerable.py:20  weak-hash: hashlib.md5() is not collision-resistant; avoid for security use
[HIGH] samples/vulnerable.py:29  sql-injection: execute() built from string interpolation; use parameterized queries

6 finding(s), 5 high severity
```

Note the `weak_digest_for_cache_key` function at line 25 also calls
`hashlib.md5()` but is suppressed (see below) and correctly does not
appear in the findings.

## Suppressing findings

A trailing comment silences findings on that line, for cases a human has
reviewed and accepted:

```python
hashlib.md5(data).hexdigest()  # minisast: ignore[weak-hash]
eval(trusted_expr)             # minisast: ignore
```

- `# minisast: ignore[rule-id, other-rule]` suppresses only the listed rules.
- `# minisast: ignore` (no brackets) suppresses every rule on that line.

Suppression is per-line and intentionally has no wildcard or file-level
form — each one should be a deliberate, visible decision next to the code
it applies to.

## Current rules

| Rule | Severity | Detects |
|------|----------|---------|
| `hardcoded-secret` | HIGH | string literal assigned to a password/secret/token/api_key-named variable |
| `eval-exec` | HIGH | calls to `eval()` / `exec()` |
| `shell-injection` | HIGH | `subprocess.*(..., shell=True)` |
| `weak-hash` | LOW | `hashlib.md5()` / `hashlib.sha1()` |
| `sql-injection` | HIGH | `.execute()`/`.executemany()` called with an f-string or `+`/`%`-built string instead of parameters |

## Vision / growth plan

This is the first slice. Future increments:

- ~~Inline suppression comments (`# minisast: ignore[rule-id]`)~~ done
- A config file for severity overrides and path excludes
- JSON/SARIF output mode for CI integration
- More rules: insecure deserialization (`pickle.loads`), YAML `load` without
  `SafeLoader`, weak TLS verification (`verify=False`), regex DoS patterns
- A small unit test suite with fixtures per rule
- Optional JS/TS support via a second, lighter rule set

## Fixture

`samples/vulnerable.py` is a fake, non-executed fixture used only to
exercise the scanner's rules — every "credential" in it is invented for
this repo.
