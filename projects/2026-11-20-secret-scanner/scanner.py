"""secret-scanner: a defensive scanner that finds accidentally committed secrets.

Two detectors:
  * rules   - regexes for well-known token shapes (AWS key id, GitHub token, private key header...)
  * entropy - high Shannon-entropy strings assigned to suspicious-looking names
Suppression:
  * inline  - `# scanner:ignore` or `# scanner:ignore=rule1,rule2` on the offending line
  * paths   - glob patterns in `<root>/.secretignore`
Modes: scan a whole tree, or only the lines a git diff adds (pre-commit style).
Findings are always printed *redacted* so the scanner itself never re-leaks a secret.
Exit status: 0 clean, 1 findings, 2 usage or git error.
"""
import argparse
import fnmatch
import math
import os
import re
import sys
from collections import Counter, namedtuple

import baseline
import gitdiff

# `path` is what we print; `rel_path` is root-relative with "/" separators, so
# tree and diff scans fingerprint the same secret identically.
Finding = namedtuple("Finding", "path line rule redacted rel_path fingerprint")

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

# Inline suppression: `# scanner:ignore` silences every rule on that line,
# `# scanner:ignore=jwt,github-token` silences only the named rules.
IGNORE = re.compile(r"scanner:ignore(?:=([\w,-]+))?")


def shannon(s):
    """Bits of entropy per character."""
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def redact(s, keep=4):
    return s[:keep] + "*" * max(0, len(s) - keep)


def ignored_rules(line):
    """Return None (no directive), set() (ignore all) or a set of rule names."""
    m = IGNORE.search(line)
    if not m:
        return None
    return set(m.group(1).split(",")) if m.group(1) else set()


def load_ignore_file(path):
    """Read glob patterns (one per line, '#' comments) from `path`."""
    try:
        with open(path, encoding="utf-8") as fh:
            return [l.strip() for l in fh if l.strip() and not l.lstrip().startswith("#")]
    except OSError:
        return []


def path_allowed(path, patterns):
    """True if the relative path, or any path component, matches an allowlist glob."""
    norm = path.replace(os.sep, "/")
    parts = norm.split("/")
    return any(fnmatch.fnmatch(norm, p) or any(fnmatch.fnmatch(x, p) for x in parts) for p in patterns)


def scan_line(line, entropy_threshold=3.5):
    """Yield (rule, redacted_match) for one line, honouring inline ignores."""
    for rule, raw in _match_line(line, entropy_threshold):
        yield rule, redact(raw)


def _match_line(line, entropy_threshold=3.5):
    """Like scan_line but yields raw matches; never print or store these."""
    skip = ignored_rules(line)
    if skip is not None and not skip:
        return  # blanket ignore
    skip = skip or set()
    for name, rx in RULES:
        if name in skip:
            continue
        for m in rx.finditer(line):
            yield name, m.group(0)
    if "high-entropy-assignment" in skip:
        return
    for m in ASSIGN.finditer(line):
        val = m.group(2)
        if shannon(val) >= entropy_threshold and not PLACEHOLDER.search(val):
            yield "high-entropy-assignment", val


def line_findings(path, rel_path, no, line):
    rel_path = rel_path.replace(os.sep, "/")
    for rule, raw in _match_line(line):
        yield Finding(path, no, rule, redact(raw), rel_path,
                      baseline.fingerprint(rel_path, rule, raw))


def scan_path(root, allow=()):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules"}]
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root)
            if f == ".secretignore" or path_allowed(rel, allow):
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue  # binary / unreadable
            for no, line in enumerate(text.splitlines(), 1):
                yield from line_findings(path, rel, no, line)


def scan_diff(diff_text, allow=()):
    """Yield a Finding for each secret on a line added by a unified diff."""
    for path, no, line in gitdiff.added_lines(diff_text):
        if os.path.basename(path) == ".secretignore" or path_allowed(path, allow):
            continue
        yield from line_findings(path, path, no, line)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan for accidentally committed secrets.")
    ap.add_argument("root", nargs="?", default="samples", help="directory to scan")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="scan lines added in the git index")
    mode.add_argument("--since", metavar="REV", help="scan lines added since REV (tracked files)")
    mode.add_argument("--diff", metavar="FILE", help="scan a unified diff file ('-' = stdin)")
    base = ap.add_mutually_exclusive_group()
    base.add_argument("--baseline", metavar="FILE", help="suppress findings recorded in FILE")
    base.add_argument("--write-baseline", metavar="FILE",
                      help="record all current findings to FILE (tree scan only)")
    args = ap.parse_args(argv)
    diff_mode = args.staged or args.since is not None or args.diff is not None
    if args.write_baseline is not None and diff_mode:
        ap.error("--write-baseline needs a full tree scan, not a diff mode")

    if not os.path.isdir(args.root):
        ap.error("not a directory: %s" % args.root)  # never report a typo as "clean"
    allow = load_ignore_file(os.path.join(args.root, ".secretignore"))

    try:
        # Load first: a missing or corrupt baseline must fail loudly (exit 2).
        known = None if args.baseline is None else baseline.load(args.baseline)
        if args.diff == "-":
            findings = scan_diff(sys.stdin.buffer.read().decode("utf-8", "replace"), allow)
        elif args.diff is not None:
            with open(args.diff, "rb") as fh:
                findings = scan_diff(fh.read().decode("utf-8", "replace"), allow)
        elif args.staged or args.since is not None:
            findings = scan_diff(gitdiff.git_diff(args.root, args.staged, args.since), allow)
        else:
            findings = scan_path(args.root, allow)
        findings = list(findings)
        if args.write_baseline is not None:
            refused = baseline.write(args.write_baseline, findings)
            print("baselined %d finding(s)" % (len(findings) - refused))
            if refused:
                print("%d finding(s) cannot be baselined; they will keep failing scans" % refused)
            return 1 if refused else 0
    except (OSError, RuntimeError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    summary = ""
    if known is not None:
        findings, suppressed, unused = baseline.apply(findings, known)
        summary = ", %d suppressed by baseline" % suppressed
        if unused and not diff_mode:  # a diff only sees part of the tree
            summary += ", %d stale baseline match(es): consider rewriting it" % unused
    for f in findings:
        print("%s:%d  [%s]  %s" % (f.path, f.line, f.rule, f.redacted))
    print("%d finding(s)%s" % (len(findings), summary))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
