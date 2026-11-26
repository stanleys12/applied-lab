"""Baseline of known findings, so only *new* secrets fail a scan.

A fingerprint hashes (relative path, rule, matched value). Line numbers are left
out so a baseline survives unrelated edits. Each entry has a count: adding one
more copy of a known secret to the same file is still reported by a tree scan.
(A diff scan sees only added lines, so it cannot count pre-existing copies.)

The raw value is never stored. The digest is unsalted, though, so someone who has
the file could test guesses against it: treat a baseline as a record of leaks to
rotate and clean up, not as a safe place to keep them.
"""
import hashlib
import json
from collections import Counter

VERSION = 1

# These rules match only a fixed marker, not the secret itself, so every hit in a
# file would share a fingerprint and a *new* key could hide behind an old entry.
UNBASELINABLE = {"private-key-block"}


def fingerprint(rel_path, rule, secret):
    blob = "\0".join((rel_path, rule, secret)).encode("utf-8", "surrogateescape")
    return hashlib.sha256(blob).hexdigest()


def write(path, findings):
    """Save `findings` to `path`. Return how many could not be baselined."""
    counts, meta, refused = Counter(), {}, 0
    for f in findings:
        if f.rule in UNBASELINABLE:
            refused += 1
            continue
        counts[f.fingerprint] += 1
        meta[f.fingerprint] = (f.rel_path, f.rule)
    entries = [{"path": meta[k][0], "rule": meta[k][1], "fingerprint": k, "count": counts[k]}
               for k in sorted(counts, key=lambda k: (meta[k], k))]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"version": VERSION, "findings": entries}, fh, indent=2)
        fh.write("\n")
    return refused


def load(path):
    """Return Counter{fingerprint: count}. Raise ValueError if the file is invalid."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)  # JSONDecodeError is a ValueError
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise ValueError("%s: not a version %d baseline" % (path, VERSION))
    entries = data.get("findings")
    if not isinstance(entries, list):
        raise ValueError("%s: 'findings' must be a list" % path)
    known = Counter()
    for e in entries:
        fp = e.get("fingerprint") if isinstance(e, dict) else None
        count = e.get("count") if isinstance(e, dict) else None
        if not isinstance(fp, str) or type(count) is not int or count < 1:
            raise ValueError("%s: malformed entry %r" % (path, e))
        known[fp] += count
    return known


def apply(findings, known):
    """Split findings into (new, suppressed_count, unused_baseline_count)."""
    remaining = Counter(known)
    new, suppressed = [], 0
    for f in findings:
        if f.rule not in UNBASELINABLE and remaining[f.fingerprint] > 0:
            remaining[f.fingerprint] -= 1
            suppressed += 1
        else:
            new.append(f)
    return new, suppressed, sum(remaining.values())
