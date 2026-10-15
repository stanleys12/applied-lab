"""Content-Security-Policy parser and weakness auditor (defensive, offline)."""
import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass

@dataclass
class Finding:
    severity: str  # high | medium | low
    directive: str
    message: str


def parse(header):
    """Parse a CSP string into {directive: [sources]}. First duplicate wins, per spec."""
    policy = {}
    for part in header.split(";"):
        tokens = part.split()
        if not tokens:
            continue
        name = tokens[0].lower()
        policy.setdefault(name, tokens[1:])
    return policy


def audit(policy):
    findings = []
    add = lambda sev, d, msg: findings.append(Finding(sev, d, msg))
    effective = policy.get("script-src", policy.get("default-src"))
    if effective is None:
        add("high", "script-src", "no script-src or default-src: scripts are unrestricted")
    # default-src only governs scripts when script-src is absent.
    governing = [d for d in ("script-src", "script-src-elem") if d in policy]
    if "script-src" not in policy and "default-src" in policy:
        governing.append("default-src")
    for d in governing:
        for src in policy.get(d, []):
            s = src.lower()
            if s == "'unsafe-inline'" and not _has_nonce_or_hash(policy.get(d, [])):
                add("high", d, "'unsafe-inline' allows inline script injection (XSS)")
            elif s == "'unsafe-eval'":
                add("medium", d, "'unsafe-eval' allows eval()-style code execution")
            elif s in ("*", "http:", "https:", "data:"):
                add("high", d, f"{src!r} allows scripts from almost anywhere")
            elif s.startswith("*.") or s.startswith("http://"):
                add("medium", d, f"{src!r} is overly broad or not HTTPS-only")
    findings.extend(audit_nonces(policy))
    if "object-src" not in policy and "default-src" not in policy:
        add("medium", "object-src", "object-src missing: plugins can be a script vector")
    if "base-uri" not in policy:
        add("medium", "base-uri", "base-uri missing: injected <base> can hijack relative URLs")
    if "frame-ancestors" not in policy:
        add("low", "frame-ancestors", "frame-ancestors missing: clickjacking not mitigated by CSP")
    return findings


NONCE_RE = re.compile(r"^'nonce-([^']*)'$", re.I)
B64_RE = re.compile(r"^[A-Za-z0-9+/_-]+={0,2}$")


def nonces(policy):
    """All nonce values (without quotes) used anywhere in the policy."""
    return [m.group(1) for srcs in policy.values() for s in srcs if (m := NONCE_RE.match(s))]


def audit_nonces(policy):
    """Nonce hygiene: spec wants >=128 bits of entropy, base64 charset, unique per response."""
    out = []
    for n in nonces(policy):
        if not B64_RE.match(n):
            out.append(Finding("medium", "script-src", f"nonce {n!r} is not valid base64/base64url"))
        elif len(n) < 22:  # 16 random bytes encode to >=22 base64 chars
            out.append(Finding("medium", "script-src", f"nonce {n!r} is under 128 bits; guessable"))
    scripts = policy.get("script-src", policy.get("default-src", []))
    has_trust = any(s.lower().startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-")) for s in scripts)
    if any(s.lower() == "'strict-dynamic'" for s in scripts) and not has_trust:
        out.append(Finding("medium", "script-src",
                           "'strict-dynamic' without nonce/hash has no effect and drops host allowlists"))
    return out


def _has_nonce_or_hash(sources):
    # With a nonce/hash, modern browsers ignore 'unsafe-inline', so it is only a fallback.
    return any(s.lower().startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-")) for s in sources)


WEIGHTS = {"high": 30, "medium": 10, "low": 3}
RANK = {"low": 1, "medium": 2, "high": 3}


def score(findings):
    """0-100 grade; each finding subtracts its severity weight."""
    return max(0, 100 - sum(WEIGHTS[f.severity] for f in findings))


def extract_headers(text):
    """Pull CSP values out of a raw header dump (one 'Name: value' per line).

    Returns [(header_name, value)] for enforcing and report-only policies.
    """
    found = []
    for line in text.splitlines():
        name, _, value = line.partition(":")
        if name.strip().lower() in ("content-security-policy", "content-security-policy-report-only"):
            found.append((name.strip(), value.strip()))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit a Content-Security-Policy offline.")
    ap.add_argument("policy", nargs="?", help="CSP string (default: a sample weak policy)")
    ap.add_argument("--file", help="header dump file to scan (one 'Name: value' per line)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--fail-on", choices=RANK, help="exit 1 if any finding is at/above this severity")
    args = ap.parse_args(argv)

    if args.file:
        with open(args.file) as fh:
            policies = extract_headers(fh.read())
        if not policies:
            ap.error("no Content-Security-Policy header found in file")
    else:
        policies = [("Content-Security-Policy", args.policy or
                     "default-src 'self'; script-src 'self' 'unsafe-inline' https:")]

    worst, reports = 0, []
    seen = {}  # nonce -> first header that used it
    for name, header in policies:
        policy = parse(header)
        findings = audit(policy)
        for n in set(nonces(policy)):
            if n in seen:
                findings.append(Finding("high", "script-src",
                                        f"nonce {n!r} reused (also in {seen[n]}): nonces must be unique per response"))
            seen.setdefault(n, name)
        worst = max([worst] + [RANK[f.severity] for f in findings])
        note = " (report-only: not enforced)" if name.lower().endswith("report-only") else ""
        reports.append({"header": name, "policy": header, "score": score(findings),
                        "report_only": bool(note), "findings": [asdict(f) for f in findings]})
        if not args.json:
            print(f"{name}{note}: score {score(findings)}/100\n  {header}")
            for f in findings:
                print(f"  [{f.severity:<6}] {f.directive}: {f.message}")
    if args.json:
        print(json.dumps(reports, indent=2))
    return 1 if args.fail_on and worst >= RANK[args.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
