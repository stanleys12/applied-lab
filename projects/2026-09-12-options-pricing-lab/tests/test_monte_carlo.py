"""Test suite for monte_carlo.py.

Checks:
1. The MC estimate lands within a small number of standard errors of
   the Black-Scholes closed form, across a grid of parameters -- using
   the reported stderr itself as the tolerance means the test doesn't
   need a fixed magic tolerance that could be too tight or too loose.
2. Standard error shrinks as path count grows (more sampling ->
   tighter confidence interval).
3. Antithetic variates reduce standard error vs. plain sampling at the
   same path count.
4. A fixed seed makes results reproducible.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from black_scholes import CALL, PUT, price
from monte_carlo import mc_price


class TestMatchesBlackScholes(unittest.TestCase):
    def test_within_standard_errors_across_grid(self):
        for S, K, T, sigma, option_type in (
            (100.0, 100.0, 1.0, 0.20, CALL),
            (100.0, 100.0, 1.0, 0.20, PUT),
            (110.0, 100.0, 0.5, 0.35, CALL),
            (90.0, 100.0, 2.0, 0.15, PUT),
        ):
            r = 0.04
            bs = price(S, K, T, r, sigma, option_type)
            mc, se = mc_price(S, K, T, r, sigma, option_type, n_paths=50000, seed=123)
            self.assertLessEqual(
                abs(mc - bs), 4 * se,
                msg=f"S={S} K={K} T={T} sigma={sigma} type={option_type}: "
                    f"mc={mc:.4f}+/-{se:.4f} vs bs={bs:.4f}",
            )


class TestStandardErrorShrinks(unittest.TestCase):
    def test_more_paths_means_smaller_stderr(self):
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
        _, se_small = mc_price(S, K, T, r, sigma, CALL, n_paths=1000, seed=1)
        _, se_large = mc_price(S, K, T, r, sigma, CALL, n_paths=50000, seed=1)
        self.assertLess(se_large, se_small)


class TestAntitheticReducesVariance(unittest.TestCase):
    def test_antithetic_stderr_below_plain(self):
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
        _, se_plain = mc_price(S, K, T, r, sigma, CALL, n_paths=20000, antithetic=False, seed=7)
        _, se_anti = mc_price(S, K, T, r, sigma, CALL, n_paths=20000, antithetic=True, seed=7)
        self.assertLess(se_anti, se_plain)


class TestReproducibility(unittest.TestCase):
    def test_same_seed_same_result(self):
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
        result_a = mc_price(S, K, T, r, sigma, CALL, n_paths=5000, seed=99)
        result_b = mc_price(S, K, T, r, sigma, CALL, n_paths=5000, seed=99)
        self.assertEqual(result_a, result_b)


class TestInputValidation(unittest.TestCase):
    def test_invalid_option_type_raises(self):
        with self.assertRaises(ValueError):
            mc_price(100, 100, 1, 0.05, 0.2, option_type="straddle")


if __name__ == "__main__":
    unittest.main()
