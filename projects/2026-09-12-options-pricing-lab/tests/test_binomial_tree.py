"""Test suite for binomial_tree.py.

Checks:
1. Convergence: the European CRR tree price approaches the
   Black-Scholes closed form as the step count grows.
2. American calls (non-dividend stock) never exceed their European
   counterpart in value -- early exercise is never optimal for a call
   without dividends, so the two must match.
3. American puts are worth at least as much as European puts, since
   the extra early-exercise right can only add value.
4. Deep ITM American puts are worth their intrinsic value at minimum.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binomial_tree import AMERICAN, EUROPEAN, crr_price
from black_scholes import CALL, PUT, price


class TestConvergesToBlackScholes(unittest.TestCase):
    def test_european_tree_converges(self):
        S, K, T, r, sigma = 100.0, 95.0, 0.5, 0.04, 0.25
        bs = price(S, K, T, r, sigma, CALL)
        tree_coarse = crr_price(S, K, T, r, sigma, CALL, EUROPEAN, n=20)
        tree_fine = crr_price(S, K, T, r, sigma, CALL, EUROPEAN, n=500)
        # The fine tree should be noticeably closer to the analytic
        # price than the coarse tree.
        self.assertLess(abs(tree_fine - bs), abs(tree_coarse - bs))
        self.assertAlmostEqual(tree_fine, bs, delta=0.02)


class TestAmericanVsEuropean(unittest.TestCase):
    def test_american_call_equals_european_call(self):
        # No dividends -> early exercise of a call is never optimal.
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
        american = crr_price(S, K, T, r, sigma, CALL, AMERICAN, n=200)
        european = crr_price(S, K, T, r, sigma, CALL, EUROPEAN, n=200)
        self.assertAlmostEqual(american, european, delta=1e-6)

    def test_american_put_at_least_european_put(self):
        for S in (80.0, 100.0, 120.0):
            american = crr_price(S, 100.0, 1.0, 0.05, 0.20, PUT, AMERICAN, n=200)
            european = crr_price(S, 100.0, 1.0, 0.05, 0.20, PUT, EUROPEAN, n=200)
            self.assertGreaterEqual(american, european - 1e-9, msg=f"S={S}")

    def test_deep_itm_american_put_at_least_intrinsic(self):
        S, K, T, r, sigma = 50.0, 100.0, 1.0, 0.05, 0.20
        american = crr_price(S, K, T, r, sigma, PUT, AMERICAN, n=200)
        self.assertGreaterEqual(american, (K - S) - 1e-6)


class TestInputValidation(unittest.TestCase):
    def test_invalid_option_type_raises(self):
        with self.assertRaises(ValueError):
            crr_price(100, 100, 1, 0.05, 0.2, option_type="straddle")

    def test_invalid_exercise_style_raises(self):
        with self.assertRaises(ValueError):
            crr_price(100, 100, 1, 0.05, 0.2, exercise="bermudan")


if __name__ == "__main__":
    unittest.main()
