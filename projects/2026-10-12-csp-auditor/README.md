# csp-auditor

Offline, defensive Content-Security-Policy auditor (stdlib only). Give it a CSP header
string; it parses the policy and reports weaknesses that undermine XSS protection.

## Vision
Grow from a single-header linter into a small HTTP security-header auditor: severity
scoring, file/batch input, report-only policies, nonce reuse checks, and cookie/HSTS rules.

## Run
    python3 csp.py "default-src 'self'; script-src 'self' 'unsafe-eval'"
    python3 csp.py --file sample_headers.txt --fail-on high --json
    python3 test_csp.py

## Increments
1. CSP parser + rule-based auditor (unsafe-inline/eval, wildcard sources, missing object-src/base-uri/frame-ancestors) (done)
2. Scoring (0-100), header-dump input (`--file`, report-only aware), `--json`, `--fail-on` exit codes for CI; CLI tests (done)
3. Nonce hygiene: length (<128-bit), base64 charset, `'strict-dynamic'` without nonce/hash, nonce reuse across headers in a dump (done)
4. `--all-headers`: HSTS max-age, Set-Cookie Secure/HttpOnly/SameSite, nosniff, Referrer-Policy audit (done)
5. Cookie hardening: `__Host-`/`__Secure-` prefix rules, `SameSite=None` needs Secure; HSTS preload requirements; single file read (done)
