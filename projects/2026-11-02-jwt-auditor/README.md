# jwt-auditor

Offline, defensive JSON Web Token inspector (stdlib only). It decodes a token and flags
header/claim weaknesses. It never verifies, forges, or guesses secrets.

## Vision
Grow into a small JWT review toolkit: claim-policy checks, batch/log scanning, JSON output
and CI exit codes, and a verifier-config checklist.

## Run
    python3 jwt_audit.py <token>
    python3 test_jwt_audit.py

## Increments
1. Decoder + rule-based auditor (alg none/missing, key-URL headers, kid metachars, exp/claims) (1/5)
