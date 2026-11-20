"""secret-scanner: a defensive scanner that finds accidentally committed secrets.

Two detectors:
  * rules   - regexes for well-known token shapes (AWS key id, GitHub token, private key header...)
  * entropy - high Shannon-entropy strings assigned to suspicious-looking names
Findings are always printed *redacted* so the scanner itself never re-leaks a secret.
"""
import math
import os
import re
import sys
from collections import Counter

RULES = [
    ("aws-access-key-id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
]
ASSIGN = re.compile(r"""(?i)(secret|token|passw(?:or)?d|api[_-]?key|auth)\w*\s*[:=]\s*['"]([^'"\s]{16,})['"]""")


# Dictionary-word placeholders score high on entropy but are not real secrets.
PLACEHOLDER = re.compile(r"(?i)password|example|changeme|placeholder|your[_-]?(key|token)|1234567890")


def shannon(s):
    """Bits of entropy per character."""
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def redact(s, keep=4):
    return s[:keep] + "*" * max(0, len(s) - keep)


def scan_text(text, entropy_threshold=3.5):
    """Yield (line_no, rule, redacted_match) for every finding in `text`."""
    for no, line in enumerate(text.splitlines(), 1):
        for name, rx in RULES:
            for m in rx.finditer(line):
                yield no, name, redact(m.group(0))
        for m in ASSIGN.finditer(line):
            val = m.group(2)
            if shannon(val) >= entropy_threshold and not PLACEHOLDER.search(val):
                yield no, "high-entropy-assignment", redact(val)


def scan_path(root):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules"}]
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue  # binary / unreadable
            for no, rule, red in scan_text(text):
                yield path, no, rule, red


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "samples"
    n = 0
    for path, no, rule, red in scan_path(root):
        print("%s:%d  [%s]  %s" % (path, no, rule, red))
        n += 1
    print("%d finding(s)" % n)
    sys.exit(1 if n else 0)
