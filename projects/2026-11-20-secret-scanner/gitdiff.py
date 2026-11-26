"""Extract the *added* lines from a unified diff, with their new-file line numbers.

Parsing is driven by the line counts in each `@@` header, so file content that
merely looks like a header (an added line starting "++ " renders as "+++ ") is
never mistaken for one.
"""
import re
import subprocess

HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def unquote_path(raw):
    """Decode a `+++ ` path: drop the trailing TAB and undo git's C-style quoting."""
    raw = raw.split("\t")[0]
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        # unicode_escape yields one code point per byte for octal escapes, so
        # round-trip through latin-1 to recover the original UTF-8 bytes.
        body = raw[1:-1].encode("utf-8").decode("unicode_escape")
        raw = body.encode("latin-1", "replace").decode("utf-8", "replace")
    return raw


def added_lines(diff_text):
    """Yield (path, new_line_no, text) for every added line in a unified diff."""
    path, old_left, new_left, new_no = None, 0, 0, 0
    # Split on newline only: str.splitlines() also breaks on form feeds and
    # other separators that git treats as ordinary content.
    for line in diff_text.split("\n"):
        if old_left > 0 or new_left > 0:  # inside a hunk body
            tag = line[:1]
            if tag == "+":
                if path is not None:
                    yield path, new_no, line[1:].rstrip("\r")
                new_no += 1
                new_left -= 1
            elif tag == "-":
                old_left -= 1
            elif tag != "\\":  # context line ("\ No newline..." counts for nothing)
                old_left -= 1
                new_left -= 1
                new_no += 1
            continue
        if line.startswith("+++ "):
            target = unquote_path(line[4:])
            if target == "/dev/null":  # file deletion
                path = None
            else:
                path = target[2:] if target.startswith("b/") else target
            continue
        m = HUNK.match(line)
        if m:
            old_left = int(m.group(1) if m.group(1) is not None else 1)
            new_no = int(m.group(2))
            new_left = int(m.group(3) if m.group(3) is not None else 1)


def git_diff(root, staged=False, rev=None):
    """Return the diff text for `root`. Paths come back relative to `root`.

    Compares the index to HEAD (`staged`) or `rev` to the working tree.
    Raises RuntimeError if git fails.
    """
    # Pin the output format so user config (external diff drivers, textconv,
    # custom prefixes) cannot change or hide what gets scanned.
    cmd = ["git", "-C", root, "-c", "core.quotepath=false", "diff", "--unified=0",
           "--no-color", "--no-ext-diff", "--no-textconv", "--relative",
           "--src-prefix=a/", "--dst-prefix=b/"]
    if staged:
        cmd.append("--cached")
    if rev is not None:
        if rev.startswith("-"):
            raise RuntimeError("invalid revision: %r" % rev)
        cmd.append(rev)
    cmd.append("--")
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except OSError as exc:
        raise RuntimeError("could not run git: %s" % exc)
    if proc.returncode != 0:
        msg = proc.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(msg or "git diff failed")
    return proc.stdout.decode("utf-8", "replace")
