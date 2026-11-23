# secret-scanner

Defensive tool: find secrets accidentally left in source trees, the way pre-commit hooks do.
All sample credentials are fake. Findings are printed redacted.

## Vision
Regex rules + entropy detection -> allowlist / inline ignore -> git-diff mode (scan only added
lines) -> baseline file for known findings -> JSON output & precision/recall test corpus.

## Run
    python3 scanner.py samples

## Increments
1. Rule regexes + entropy-on-assignment detector, redacted output, tree walker (done)
2. Suppression: inline `# scanner:ignore[=rule,...]` and a `.secretignore` path-glob allowlist; unit tests (`python3 tests/test_ignore.py`) (done)
