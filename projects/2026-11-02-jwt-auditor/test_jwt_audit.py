import base64
import json
import os
import subprocess
import sys
import tempfile
import time
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


class PolicyTests(unittest.TestCase):
    def pcodes(self, header, payload, policy):
        r = ja.audit_token(make(header, payload), NOW, policy)
        return {f["code"] for f in r["findings"]}

    def test_all_policy_checks_pass(self):
        pol = {"allow_algs": ["RS256"], "iss": "me", "aud": "you"}
        self.assertEqual(self.pcodes({"alg": "RS256"}, GOOD_PAYLOAD, pol), set())

    def test_policy_violations(self):
        pol = {"allow_algs": ["ES256"], "iss": "other", "aud": "nobody"}
        self.assertEqual(self.pcodes({"alg": "RS256"}, GOOD_PAYLOAD, pol),
                         {"POLICY_ALG", "POLICY_ISS", "POLICY_AUD"})

    def test_aud_array(self):
        p = dict(GOOD_PAYLOAD, aud=["x", "you"])
        self.assertEqual(self.pcodes({"alg": "RS256"}, p, {"aud": "you"}), set())

    def test_nbf_future(self):
        p = dict(GOOD_PAYLOAD, nbf=NOW + 30)
        self.assertIn("NOT_YET_VALID", self.pcodes({"alg": "RS256"}, p, None))

    def test_cli_policy_flags(self):
        t = make({"alg": "RS256"}, GOOD_PAYLOAD)
        out = subprocess.run([sys.executable, os.path.join(HERE, "jwt_audit.py"), t,
                              "--expect-iss", "evil"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("POLICY_ISS", out.stdout)


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(HERE, "jwt_audit.py"), *args],
                              capture_output=True, text=True)

    def test_file_batch_json_and_exit_codes(self):
        bad = make({"alg": "none"}, GOOD_PAYLOAD, "")
        ok = make({"alg": "RS256"}, dict(GOOD_PAYLOAD, iat=int(time.time()) - 60, exp=int(time.time()) + 600))
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


class ExtraChecksTests(unittest.TestCase):
    def test_iat_future_crit_typ(self):
        p = dict(GOOD_PAYLOAD, iat=NOW + 3600, exp=NOW + 7200)
        c = codes(make({"alg": "RS256", "crit": ["b64"], "typ": "weird"}, p))
        self.assertTrue({"IAT_FUTURE", "HEADER_CRIT", "TYP_UNUSUAL"} <= c)

    def test_small_iat_skew_tolerated(self):
        p = dict(GOOD_PAYLOAD, iat=NOW + 30)
        self.assertNotIn("IAT_FUTURE", codes(make({"alg": "RS256"}, p)))

    def test_max_lifetime_policy(self):
        tok = make({"alg": "RS256"}, GOOD_PAYLOAD)  # lifetime 660s
        f = lambda pol: {x["code"] for x in ja.audit_token(tok, NOW, pol)["findings"]}
        self.assertIn("POLICY_LIFETIME", f({"max_lifetime": 300}))
        self.assertNotIn("POLICY_LIFETIME", f({"max_lifetime": 3600}))
        noiat = make({"alg": "RS256"}, {k: v for k, v in GOOD_PAYLOAD.items() if k != "iat"})
        g = {x["code"] for x in ja.audit_token(noiat, NOW, {"max_lifetime": 300})["findings"]}
        self.assertIn("POLICY_LIFETIME_UNKNOWN", g)


class BatchTests(unittest.TestCase):
    def test_duplicate_jti_flagged_on_both(self):
        a = ja.audit_token(make({"alg": "RS256"}, dict(GOOD_PAYLOAD, jti="x1")), NOW)
        b = ja.audit_token(make({"alg": "RS256"}, dict(GOOD_PAYLOAD, jti="x1")), NOW)
        c = ja.audit_token(make({"alg": "RS256"}, dict(GOOD_PAYLOAD, jti="x2")), NOW)
        ja.batch_checks([a, b, c])
        self.assertEqual([r["findings"] != [] for r in (a, b, c)], [True, True, False])
        self.assertIn("tokens 1, 2", a["findings"][0]["message"])

    def test_malformed_has_no_payload_and_summary_counts(self):
        bad = ja.audit_token("nope", NOW)
        none_tok = ja.audit_token(make({"alg": "none"}, GOOD_PAYLOAD, ""), NOW)
        s = ja.summarize(ja.batch_checks([bad, none_tok]))
        self.assertEqual(s["tokens"], 2)
        self.assertEqual(s["by_code"]["MALFORMED"], 1)
        self.assertGreaterEqual(s["by_severity"]["high"], 2)

    def test_cli_summary_flag(self):
        p = subprocess.run([sys.executable, os.path.join(HERE, "jwt_audit.py"), "garbage",
                            "--summary", "--json"], capture_output=True, text=True)
        data = json.loads(p.stdout)
        self.assertEqual(data["summary"]["by_code"], {"MALFORMED": 1})


if __name__ == "__main__":
    unittest.main()
