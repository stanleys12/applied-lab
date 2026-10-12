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
            "default-src 'none'; script-src 'nonce-x' 'strict-dynamic'; object-src 'none'; "
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


if __name__ == "__main__":
    unittest.main()
