import math
import unittest
from var import (historical_var, historical_cvar, parametric_var, parametric_cvar,
                 synthetic_returns, backtest, kupiec_pof,
                 monte_carlo_var, excess_kurtosis, traffic_light, binom_cdf)


class VarTests(unittest.TestCase):
    def test_historical_var_known_quantile(self):
        returns = [-i / 100 for i in range(1, 101)]  # losses 1%..100%
        self.assertAlmostEqual(historical_var(returns, 0.95), 0.95)

    def test_cvar_at_least_var(self):
        r = synthetic_returns()
        for a in (0.9, 0.95, 0.99):
            self.assertGreaterEqual(historical_cvar(r, a), historical_var(r, a))
            self.assertGreaterEqual(parametric_cvar(r, a), parametric_var(r, a))

    def test_higher_confidence_higher_var(self):
        r = synthetic_returns()
        self.assertGreater(historical_var(r, 0.99), historical_var(r, 0.95))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            historical_var([])

    def test_fat_tails_break_normal_assumption(self):
        r = synthetic_returns(n=5000)
        self.assertGreater(historical_cvar(r, 0.99), parametric_cvar(r, 0.99) * 0.9)


class MonteCarloTests(unittest.TestCase):
    def test_normal_mc_close_to_parametric(self):
        r = synthetic_returns(n=2000)
        v, c = monte_carlo_var(r, 0.99, "normal", n_sims=100000)
        self.assertAlmostEqual(v, parametric_var(r, 0.99), delta=0.002)
        self.assertGreaterEqual(c, v)

    def test_t_has_fatter_tail_than_normal_at_99(self):
        r = synthetic_returns(n=3000)
        self.assertGreater(excess_kurtosis(r), 0.5)
        _, c_n = monte_carlo_var(r, 0.99, "normal", n_sims=100000)
        _, c_t = monte_carlo_var(r, 0.99, "t", n_sims=100000)
        self.assertGreater(c_t, c_n)

    def test_deterministic_seed_and_bad_dist(self):
        r = synthetic_returns()
        self.assertEqual(monte_carlo_var(r, dist="t"), monte_carlo_var(r, dist="t"))
        with self.assertRaises(ValueError):
            monte_carlo_var(r, dist="laplace")


class BacktestTests(unittest.TestCase):
    def test_kupiec_perfect_rate_not_rejected(self):
        lr, p = kupiec_pof(5, 500, 0.99)
        self.assertAlmostEqual(lr, 0.0, places=9)
        self.assertGreater(p, 0.99)

    def test_kupiec_known_value(self):
        # 10 hits in 250 at 99%: LR = 2*(48.4638 - 41.9859) = 12.956 by hand, clearly rejected
        lr, p = kupiec_pof(10, 250, 0.99)
        self.assertAlmostEqual(lr, 12.956, places=2)
        self.assertLess(p, 0.001)

    def test_kupiec_zero_hits(self):
        lr, p = kupiec_pof(0, 250, 0.99)
        self.assertAlmostEqual(lr, -2 * 250 * math.log(0.99), places=9)
        self.assertLess(p, 0.05)  # too few hits is also rejected: VaR is over-conservative

    def test_backtest_counts_window(self):
        r = synthetic_returns(n=600)
        hits, n = backtest(r, historical_var, 0.99, 250)
        self.assertEqual(n, 350)
        self.assertTrue(0 <= hits <= n)

    def test_traffic_light_matches_basel_zones(self):
        zones = [traffic_light(h) for h in range(0, 13)]
        self.assertEqual(zones[:5], ["green"] * 5)
        self.assertEqual(zones[5:10], ["yellow"] * 5)
        self.assertEqual(zones[10:], ["red"] * 3)

    def test_binom_cdf_edges(self):
        self.assertAlmostEqual(binom_cdf(250, 250, 0.01), 1.0)
        self.assertAlmostEqual(binom_cdf(0, 10, 0.5), 1 / 1024)

    def test_backtest_short_series(self):
        with self.assertRaises(ValueError):
            backtest([0.01] * 10, historical_var)


if __name__ == "__main__":
    unittest.main()
