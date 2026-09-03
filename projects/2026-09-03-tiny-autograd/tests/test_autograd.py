"""Gradient-checking test suite: for each expression, compare the
analytic gradient from Value.backward() against a central-difference
numerical estimate. This is the standard way to catch a wrong backward
rule -- the kind of bug a normal unit test (which only checks .data)
would sail right past.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autograd import Value

EPS = 1e-6
TOL = 1e-4


def numeric_grad(f, args, i):
    """Central-difference derivative of f(*args) w.r.t. args[i]."""
    plus = list(args)
    minus = list(args)
    plus[i] = args[i] + EPS
    minus[i] = args[i] - EPS
    plus_out = f(*(Value(a) for a in plus))
    minus_out = f(*(Value(a) for a in minus))
    return (plus_out.data - minus_out.data) / (2 * EPS)


def analytic_grads(f, args):
    """Run f with Value-wrapped args, backward(), and return d(out)/d(arg_i)
    for every i."""
    values = [Value(a) for a in args]
    out = f(*values)
    out.backward()
    return [v.grad for v in values]


class GradCheckMixin:
    def assert_matches_numeric(self, f, args):
        analytic = analytic_grads(f, args)
        for i, a in enumerate(analytic):
            n = numeric_grad(f, args, i)
            self.assertAlmostEqual(
                a, n, delta=TOL,
                msg=f"arg {i}: analytic={a!r} numeric={n!r} for args={args!r}",
            )


class TestBasicOps(GradCheckMixin, unittest.TestCase):
    def test_add(self):
        self.assert_matches_numeric(lambda a, b: a + b, [1.3, -2.7])

    def test_sub(self):
        self.assert_matches_numeric(lambda a, b: a - b, [4.0, 1.5])

    def test_mul(self):
        self.assert_matches_numeric(lambda a, b: a * b, [2.5, -1.1])

    def test_div(self):
        self.assert_matches_numeric(lambda a, b: a / b, [3.0, 2.0])

    def test_pow(self):
        self.assert_matches_numeric(lambda a: a ** 3, [1.7])

    def test_neg(self):
        self.assert_matches_numeric(lambda a: -a, [0.9])

    def test_tanh(self):
        self.assert_matches_numeric(lambda a: a.tanh(), [0.4])

    def test_relu_positive_branch(self):
        self.assert_matches_numeric(lambda a: a.relu(), [1.2])

    def test_relu_negative_branch(self):
        # relu is flat (grad 0) strictly below zero on both sides of x,
        # so central-difference agrees even though relu isn't smooth at 0.
        self.assert_matches_numeric(lambda a: a.relu(), [-0.8])

    def test_reflected_ops(self):
        self.assert_matches_numeric(lambda a: 2.0 + a, [1.1])
        self.assert_matches_numeric(lambda a: 3.0 - a, [1.1])
        self.assert_matches_numeric(lambda a: 2.0 * a, [1.1])
        self.assert_matches_numeric(lambda a: 5.0 / a, [1.1])


class TestCompositeExpressions(GradCheckMixin, unittest.TestCase):
    def test_shared_subexpression(self):
        # x used twice: gradient contributions must accumulate, not overwrite.
        self.assert_matches_numeric(lambda x: x * x + x, [1.5])

    def test_three_variable_tanh_expression(self):
        self.assert_matches_numeric(
            lambda a, b, c: ((a * b + c) ** 2).tanh(), [0.3, -0.5, 0.2]
        )

    def test_deeply_nested_chain(self):
        def f(x):
            y = x
            for _ in range(5):
                y = (y * 0.9 + 0.1).tanh()
            return y

        self.assert_matches_numeric(f, [0.6])


if __name__ == "__main__":
    unittest.main()
