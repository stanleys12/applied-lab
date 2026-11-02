"""jwt-auditor: offline, defensive JWT inspector. Decodes a token (never verifies or forges)
and reports header/claim weaknesses a reviewer should flag."""
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


def audit(header, payload, sig, now=None):
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
    return sorted(out, key=lambda f: -SEVERITY[f["severity"]])


def main(argv):
    if len(argv) != 2:
        print("usage: jwt_audit.py <token>", file=sys.stderr)
        return 2
    try:
        header, payload, sig = parse(argv[1])
    except ValueError as e:
        print("error:", e, file=sys.stderr)
        return 2
    print("header: ", json.dumps(header))
    print("payload:", json.dumps(payload))
    findings = audit(header, payload, sig)
    for f in findings:
        print("[%-6s] %s: %s" % (f["severity"], f["code"], f["message"]))
    return 1 if any(f["severity"] == "high" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
