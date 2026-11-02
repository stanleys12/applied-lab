import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest

import jwt_audit as ja

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = 1_800_000_000


def enc(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def make(header, payload, sig="c2ln"):
    return "%s.%s.%s" % (enc(header), enc(payload), sig)


GOOD_PAYLOAD = {"iss": "me", "aud": "you", "sub": "u1", "iat": NOW - 60, "exp": NOW + 600}


def codes(token, now=NOW):
    return {f["code"] for f in ja.audit_token(token, now)["findings"]}


class AuditTests(unittest.TestCase):
    def test_clean_token_has_no_findings_above_info(self):
        r = ja.audit_token(make({"alg": "RS256"}, GOOD_PAYLOAD), NOW)
        self.assertEqual(r["findings"], [])

    def test_alg_none_and_empty_sig(self):
        self.assertIn("ALG_NONE", codes(make({"alg": "NoNe"}, GOOD_PAYLOAD, "")))
        self.assertIn("SIG_EMPTY", codes(make({"alg": "RS256"}, GOOD_PAYLOAD, "")))

    def test_key_url_headers(self):
        self.assertIn("HEADER_KEY_URL", codes(make({"alg": "RS256", "jku": "http://x"}, GOOD_PAYLOAD)))

    def test_kid_injection(self):
        self.assertIn("KID_SUSPICIOUS", codes(make({"alg": "HS256", "kid": "../../dev/null"}, GOOD_PAYLOAD)))

    def test_exp_rules(self):
        p = dict(GOOD_PAYLOAD)
        del p["exp"]
        self.assertIn("EXP_MISSING", codes(make({"alg": "RS256"}, p)))
        p["exp"] = True
        self.assertIn("EXP_TYPE", codes(make({"alg": "RS256"}, p)))
        p["exp"] = NOW - 5
        self.assertIn("EXPIRED", codes(make({"alg": "RS256"}, p)))
        p.update(iat=NOW, exp=NOW + 86400 * 90)
        self.assertIn("LONG_LIVED", codes(make({"alg": "RS256"}, p)))

    def test_malformed(self):
        self.assertEqual(codes("not-a-jwt"), {"MALFORMED"})
        self.assertEqual(codes("a.b.c"), {"MALFORMED"})

    def test_sorted_by_severity(self):
        f = ja.audit_token(make({"alg": "none"}, {}), NOW)["findings"]
        sev = [ja.SEVERITY[x["severity"]] for x in f]
        self.assertEqual(sev, sorted(sev, reverse=True))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(HERE, "jwt_audit.py"), *args],
                              capture_output=True, text=True)

    def test_file_batch_json_and_exit_codes(self):
        bad = make({"alg": "none"}, GOOD_PAYLOAD, "")
        ok = make({"alg": "RS256"}, dict(GOOD_PAYLOAD, iat=3_999_999_000, exp=4_000_000_000))
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("# comment\n\nBearer %s\n%s\n" % (bad, ok))
        try:
            p = self.run_cli("--file", fh.name, "--json")
            self.assertEqual(p.returncode, 1)
            data = json.loads(p.stdout)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[1]["findings"], [])
            self.assertEqual(self.run_cli(ok).returncode, 0)
        finally:
            os.unlink(fh.name)

    def test_fail_on_medium(self):
        t = make({"alg": "RS256"}, {"iss": "a", "aud": "b", "sub": "c"})  # no exp -> medium
        self.assertEqual(self.run_cli(t).returncode, 0)
        self.assertEqual(self.run_cli(t, "--fail-on", "medium").returncode, 1)


if __name__ == "__main__":
    unittest.main()
