import unittest
from csp import parse, audit


def sev(header):
    return {(f.directive, f.severity) for f in audit(parse(header))}


class CspTests(unittest.TestCase):
    def test_parse_first_duplicate_wins_and_case(self):
        p = parse("Script-Src 'self'; script-src *;  ; img-src data:")
        self.assertEqual(p, {"script-src": ["'self'"], "img-src": ["data:"]})

    def test_strict_policy_is_clean(self):
        self.assertEqual(audit(parse(
            "default-src 'none'; script-src 'nonce-Zm9vYmFyYmF6cXV4MTIzNA' 'strict-dynamic'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'")), [])

    def test_unsafe_inline_flagged_unless_nonce(self):
        self.assertIn(("script-src", "high"), sev("script-src 'unsafe-inline'; object-src 'none'"))
        self.assertNotIn(("script-src", "high"), sev("script-src 'nonce-a' 'unsafe-inline'"))

    def test_no_script_restriction(self):
        self.assertIn(("script-src", "high"), sev("img-src 'self'"))

    def test_default_src_ignored_when_script_src_present(self):
        self.assertNotIn(("default-src", "high"), sev("default-src *; script-src 'self'"))
        self.assertIn(("default-src", "high"), sev("default-src *"))

    def test_eval_and_http(self):
        s = sev("script-src 'unsafe-eval' http://cdn.example")
        self.assertIn(("script-src", "medium"), s)


class NonceTests(unittest.TestCase):
    GOOD = "'nonce-Zm9vYmFyYmF6cXV4MTIzNA'"

    def test_short_nonce_flagged(self):
        self.assertIn(("script-src", "medium"), sev("script-src 'nonce-abc'; object-src 'none'"))

    def test_good_nonce_clean_of_nonce_findings(self):
        from csp import audit_nonces
        self.assertEqual(audit_nonces(parse(f"script-src {self.GOOD}")), [])

    def test_bad_charset(self):
        from csp import audit_nonces
        self.assertIn("base64", audit_nonces(parse("script-src 'nonce-ab$cdefghijklmnopqrstuvwx'"))[0].message)

    def test_strict_dynamic_needs_trust(self):
        from csp import audit_nonces
        self.assertEqual(len(audit_nonces(parse("script-src 'strict-dynamic' https://a.example"))), 1)
        self.assertEqual(audit_nonces(parse(f"script-src {self.GOOD} 'strict-dynamic'")), [])

    def test_nonce_reuse_across_headers_cli(self):
        import tempfile, os, io, contextlib
        from csp import main
        line = f"script-src {self.GOOD}; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write(f"Content-Security-Policy: {line}\nContent-Security-Policy-Report-Only: {line}\n")
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = main(["--file", fh.name, "--fail-on", "high"])
        finally:
            os.unlink(fh.name)
        self.assertEqual(rc, 1)
        self.assertIn("reused", out.getvalue())


class CliTests(unittest.TestCase):
    def test_score_and_extract(self):
        from csp import score, extract_headers
        self.assertEqual(score(audit(parse("script-src 'unsafe-inline'"))), 100 - 30 - 10 - 10 - 3 - 0)
        dump = "HTTP/1.1 200 OK\nContent-Security-Policy-Report-Only: default-src 'self'\nX-A: b"
        self.assertEqual(extract_headers(dump),
                         [("Content-Security-Policy-Report-Only", "default-src 'self'")])

    def test_fail_on_exit_code_and_json(self):
        import contextlib, io, json
        from csp import main
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["script-src *", "--json", "--fail-on", "high"]), 1)
        self.assertEqual(json.loads(out.getvalue())[0]["findings"][0]["severity"], "high")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
                                   "--fail-on", "low"]), 0)


if __name__ == "__main__":
    unittest.main()
