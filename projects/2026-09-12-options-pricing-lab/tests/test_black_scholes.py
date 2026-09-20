"""Test suite for black_scholes.py.

Three kinds of checks:
1. Put-call parity across a grid of parameters (a relationship the
   price formula must satisfy regardless of what the "correct" price
   even is).
2. A known reference price from a standard textbook example (Hull),
   to catch a formula that's internally consistent but just wrong.
3. Finite-difference checks: each analytic Greek is the derivative of
   `price()` with respect to one input, so central-difference on
   `price()` itself should match `greeks()` without needing any
   separately-derived closed form for the check.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from black_scholes import CALL, PUT, greeks, implied_vol, price

EPS = 1e-4
TOL = 1e-2


class TestPutCallParity(unittest.TestCase):
    def test_parity_holds_across_parameter_grid(self):
        for S in (80.0, 100.0, 120.0):
            for K in (90.0, 100.0, 110.0):
                for T in (0.25, 1.0, 2.0):
                    for r in (0.0, 0.03, 0.08):
                        for sigma in (0.1, 0.3, 0.6):
                            call = price(S, K, T, r, sigma, CALL)
                            put = price(S, K, T, r, sigma, PUT)
                            lhs = call - put
                            rhs = S - K * math.exp(-r * T)
                            self.assertAlmostEqual(
                                lhs, rhs, delta=1e-8,
                                msg=f"S={S} K={K} T={T} r={r} sigma={sigma}",
                            )


class TestKnownReferencePrice(unittest.TestCase):
    def test_hull_textbook_example(self):
        # Hull, "Options, Futures, and Other Derivatives": S=42, K=40,
        # r=10%, sigma=20%, T=0.5y -> call ~= 4.76, put ~= 0.81.
        call = price(S=42, K=40, T=0.5, r=0.10, sigma=0.20, option_type=CALL)
        put = price(S=42, K=40, T=0.5, r=0.10, sigma=0.20, option_type=PUT)
        self.assertAlmostEqual(call, 4.76, delta=0.01)
        self.assertAlmostEqual(put, 0.81, delta=0.01)


class TestGreeksMatchFiniteDifference(unittest.TestCase):
    def _check(self, option_type):
        S, K, T, r, sigma = 105.0, 100.0, 0.75, 0.04, 0.25
        g = greeks(S, K, T, r, sigma, option_type)

        delta_fd = (
            price(S + EPS, K, T, r, sigma, option_type)
            - price(S - EPS, K, T, r, sigma, option_type)
        ) / (2 * EPS)
        self.assertAlmostEqual(g["delta"], delta_fd, delta=TOL)

        gamma_fd = (
            price(S + EPS, K, T, r, sigma, option_type)
            - 2 * price(S, K, T, r, sigma, option_type)
            + price(S - EPS, K, T, r, sigma, option_type)
        ) / (EPS ** 2)
        self.assertAlmostEqual(g["gamma"], gamma_fd, delta=TOL)

        vega_fd = (
            price(S, K, T, r, sigma + EPS, option_type)
            - price(S, K, T, r, sigma - EPS, option_type)
        ) / (2 * EPS)
        self.assertAlmostEqual(g["vega"], vega_fd, delta=TOL)

        # theta is quoted as sensitivity to the *passage* of time, i.e.
        # -d(price)/dT.
        theta_fd = -(
            price(S, K, T + EPS, r, sigma, option_type)
            - price(S, K, T - EPS, r, sigma, option_type)
        ) / (2 * EPS)
        self.assertAlmostEqual(g["theta"], theta_fd, delta=TOL)

        rho_fd = (
            price(S, K, T, r + EPS, sigma, option_type)
            - price(S, K, T, r - EPS, sigma, option_type)
        ) / (2 * EPS)
        self.assertAlmostEqual(g["rho"], rho_fd, delta=TOL)

    def test_call_greeks(self):
        self._check(CALL)

    def test_put_greeks(self):
        self._check(PUT)


class TestImpliedVol(unittest.TestCase):
    def test_round_trip_across_parameter_grid(self):
        # Price at a known sigma, solve implied_vol from that price, and
        # recover the original sigma -- exercises the solver without
        # needing an external oracle for "correct" implied vol.
        for S in (70.0, 100.0, 140.0):
            for K in (90.0, 100.0, 110.0):
                for T in (0.1, 1.0, 2.0):
                    for sigma in (0.05, 0.2, 0.8, 1.5):
                        for option_type in (CALL, PUT):
                            r = 0.03
                            market_price = price(S, K, T, r, sigma, option_type)
                            if greeks(S, K, T, r, sigma, option_type)["vega"] < 1e-3:
                                # Deep ITM/OTM + short-dated + low-vol
                                # combos have ~0 vega: price barely moves
                                # with sigma there, so many different
                                # sigmas are indistinguishable at float
                                # precision -- implied vol is genuinely
                                # ill-posed, not a solver bug.
                                continue
                            solved = implied_vol(market_price, S, K, T, r, option_type)
                            self.assertAlmostEqual(
                                solved, sigma, delta=1e-4,
                                msg=f"S={S} K={K} T={T} sigma={sigma} type={option_type}",
                            )

    def test_unattainable_price_raises(self):
        # A call can never be worth more than the spot price itself,
        # regardless of sigma -- so this price is outside the bracket.
        with self.assertRaises(ValueError):
            implied_vol(market_price=999.0, S=100, K=100, T=1, r=0.05, option_type=CALL)


class TestInputValidation(unittest.TestCase):
    def test_invalid_option_type_raises(self):
        with self.assertRaises(ValueError):
            price(100, 100, 1, 0.05, 0.2, option_type="straddle")

    def test_nonpositive_inputs_rejected(self):
        with self.assertRaises(AssertionError):
            price(100, 100, T=0, r=0.05, sigma=0.2)
        with self.assertRaises(AssertionError):
            price(100, 100, T=1, r=0.05, sigma=0)


if __name__ == "__main__":
    unittest.main()
