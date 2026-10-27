import unittest
from var import historical_var, historical_cvar, parametric_var, parametric_cvar, synthetic_returns


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


if __name__ == "__main__":
    unittest.main()
