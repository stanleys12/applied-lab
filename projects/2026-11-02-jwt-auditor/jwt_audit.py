"""jwt-auditor: offline, defensive JWT inspector. Decodes a token (never verifies or forges)
and reports header/claim weaknesses a reviewer should flag."""
import argparse
import base64
import json
import sys
import time

SEVERITY = {"high": 3, "medium": 2, "low": 1, "info": 0}


def b64url_decode(seg):
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def parse(token):
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("expected 3 dot-separated segments (JWS), got %d" % len(parts))
    try:
        header = json.loads(b64url_decode(parts[0]))
        payload = json.loads(b64url_decode(parts[1]))
    except ValueError as e:
        raise ValueError("segment is not base64url JSON: %s" % e)
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("header and payload must be JSON objects")
    return header, payload, parts[2]


def audit(header, payload, sig, now=None, policy=None):
    now = time.time() if now is None else now
    out = []

    def add(sev, code, msg):
        out.append({"severity": sev, "code": code, "message": msg})

    alg = header.get("alg")
    if alg is None:
        add("high", "ALG_MISSING", "header has no 'alg'")
    elif str(alg).lower() == "none":
        add("high", "ALG_NONE", "alg=none: token is unsigned; servers must reject it")
    elif alg in ("HS256", "HS384", "HS512"):
        add("info", "ALG_HMAC", "HMAC alg: shared secret must be long and random; "
            "beware algorithm confusion if the verifier also accepts RSA/EC keys")
    if str(alg).lower() != "none" and not sig:
        add("high", "SIG_EMPTY", "signature segment is empty")
    for k in ("jku", "x5u", "jwk"):
        if k in header:
            add("high", "HEADER_KEY_URL", "header '%s' lets the token point at attacker-chosen "
                "keys; verifiers must ignore or allow-list it" % k)
    kid = header.get("kid")
    if isinstance(kid, str) and any(c in kid for c in ("/", "..", "'", ";", "|")):
        add("medium", "KID_SUSPICIOUS", "kid contains path/SQL metacharacters: %r" % kid)

    exp = payload.get("exp")
    if exp is None:
        add("medium", "EXP_MISSING", "no 'exp': token never expires")
    elif isinstance(exp, bool) or not isinstance(exp, (int, float)):
        add("medium", "EXP_TYPE", "'exp' is not a number")
    else:
        if exp < now:
            add("info", "EXPIRED", "token expired %ds ago" % (now - exp))
        iat = payload.get("iat")
        if isinstance(iat, (int, float)) and exp - iat > 86400 * 30:
            add("low", "LONG_LIVED", "lifetime is %.0f days" % ((exp - iat) / 86400))
    for claim in ("iss", "aud", "sub"):
        if claim not in payload:
            add("low", "CLAIM_MISSING", "no '%s' claim" % claim)
    nbf = payload.get("nbf")
    if isinstance(nbf, (int, float)) and not isinstance(nbf, bool) and nbf > now:
        add("info", "NOT_YET_VALID", "nbf is %ds in the future" % (nbf - now))
    if policy:
        out.extend(check_policy(header, payload, policy))
    return sorted(out, key=lambda f: -SEVERITY[f["severity"]])


def check_policy(header, payload, policy):
    """Compare a token against what *your* verifier is configured to accept.

    policy keys (all optional): allow_algs (list), iss (str), aud (str).
    """
    out = []
    allowed = policy.get("allow_algs")
    if allowed and header.get("alg") not in allowed:
        out.append({"severity": "high", "code": "POLICY_ALG",
                    "message": "alg %r not in allow-list %s" % (header.get("alg"), sorted(allowed))})
    iss = policy.get("iss")
    if iss and payload.get("iss") != iss:
        out.append({"severity": "high", "code": "POLICY_ISS",
                    "message": "iss %r != expected %r" % (payload.get("iss"), iss)})
    aud = policy.get("aud")
    if aud:
        got = payload.get("aud")
        got = got if isinstance(got, list) else [got]  # RFC 7519: string or array
        if aud not in got:
            out.append({"severity": "high", "code": "POLICY_AUD",
                        "message": "aud %r does not include expected %r" % (payload.get("aud"), aud)})
    return out


def audit_token(token, now=None, policy=None):
    """Parse + audit one token string; parse errors become a single high finding."""
    try:
        header, payload, sig = parse(token)
    except ValueError as e:
        return {"header": None, "payload": None,
                "findings": [{"severity": "high", "code": "MALFORMED", "message": str(e)}]}
    return {"header": header, "payload": payload, "findings": audit(header, payload, sig, now, policy)}


def read_tokens(path):
    """One token per line; blank lines and '#' comments skipped; 'Bearer ' prefix tolerated."""
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                yield line[7:].strip() if line.lower().startswith("bearer ") else line


def main(argv):
    ap = argparse.ArgumentParser(description="Offline JWT auditor (decode only, no verification)")
    ap.add_argument("token", nargs="?", help="a JWT string")
    ap.add_argument("--file", help="file with one token per line")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--allow-alg", action="append", metavar="ALG",
                    help="verifier's accepted algorithms (repeatable); others are flagged")
    ap.add_argument("--expect-iss", help="issuer your verifier requires")
    ap.add_argument("--expect-aud", help="audience your verifier requires")
    ap.add_argument("--fail-on", choices=["high", "medium", "low"], default="high",
                    help="exit 1 if any finding at or above this severity (default: high)")
    args = ap.parse_args(argv[1:])
    if bool(args.token) == bool(args.file):
        ap.error("give exactly one of <token> or --file")
    tokens = [args.token] if args.token else list(read_tokens(args.file))

    policy = {"allow_algs": args.allow_alg, "iss": args.expect_iss, "aud": args.expect_aud}
    results = [dict(audit_token(t, policy=policy), token=t[:24] + "...") for t in tokens]
    threshold = SEVERITY[args.fail_on]
    failed = any(SEVERITY[f["severity"]] >= threshold for r in results for f in r["findings"])
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for i, r in enumerate(results, 1):
            print("== token %d (%s)" % (i, r["token"]))
            if r["header"] is not None:
                print("header: ", json.dumps(r["header"]))
                print("payload:", json.dumps(r["payload"]))
            for f in r["findings"]:
                print("[%-6s] %s: %s" % (f["severity"], f["code"], f["message"]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
