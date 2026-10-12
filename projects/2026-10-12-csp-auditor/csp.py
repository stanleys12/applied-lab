"""Content-Security-Policy parser and weakness auditor (defensive, offline)."""
import sys
from dataclasses import dataclass

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
    if "object-src" not in policy and "default-src" not in policy:
        add("medium", "object-src", "object-src missing: plugins can be a script vector")
    if "base-uri" not in policy:
        add("medium", "base-uri", "base-uri missing: injected <base> can hijack relative URLs")
    if "frame-ancestors" not in policy:
        add("low", "frame-ancestors", "frame-ancestors missing: clickjacking not mitigated by CSP")
    return findings


def _has_nonce_or_hash(sources):
    # With a nonce/hash, modern browsers ignore 'unsafe-inline', so it is only a fallback.
    return any(s.lower().startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-")) for s in sources)


def main(argv):
    header = argv[1] if len(argv) > 1 else "default-src 'self'; script-src 'self' 'unsafe-inline' https:"
    print("policy:", header)
    for f in audit(parse(header)):
        print(f"  [{f.severity:<6}] {f.directive}: {f.message}")


if __name__ == "__main__":
    main(sys.argv)
