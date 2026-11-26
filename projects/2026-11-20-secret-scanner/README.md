# secret-scanner

Defensive tool: find secrets accidentally left in source trees, the way pre-commit hooks do.
All sample credentials are fake. Findings are printed redacted.

## Vision
Regex rules + entropy detection -> allowlist / inline ignore -> git-diff mode (scan only added
lines) -> baseline file for known findings -> JSON output & precision/recall test corpus.

## Run
    python3 scanner.py samples                 # whole tree
    python3 scanner.py . --staged              # only lines staged for commit
    python3 scanner.py . --since HEAD~3        # lines added since a revision
    git diff -U0 | python3 scanner.py . --diff -
    python3 -m unittest discover -s tests

Exit status is 0 when clean, 1 with findings, 2 on a usage or git error, so
`--staged` can gate a pre-commit hook. In diff modes, run with the directory that
holds `.secretignore` as `root`; allowlist paths are matched relative to it.

## Increments
1. Rule regexes + entropy-on-assignment detector, redacted output, tree walker (done)
2. Suppression: inline `# scanner:ignore[=rule,...]` and a `.secretignore` path-glob allowlist; unit tests (`python3 tests/test_ignore.py`) (done)
3. Git-diff mode (`--staged`, `--since REV`, `--diff FILE|-`): scans only added lines, with correct new-file line numbers (done)
