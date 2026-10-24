import unittest
from evaluate import precision_at_k, reciprocal_rank, ndcg_at_k, evaluate


class MetricTests(unittest.TestCase):
    def test_precision(self):
        self.assertAlmostEqual(precision_at_k([1, 2, 3], {1: 1, 3: 1}, 3), 2 / 3)

    def test_rr(self):
        self.assertEqual(reciprocal_rank([5, 6, 1], {1: 1}), 1 / 3)
        self.assertEqual(reciprocal_rank([5], {1: 1}), 0.0)

    def test_ndcg_perfect_and_reversed(self):
        rel = {1: 2, 2: 1}
        self.assertAlmostEqual(ndcg_at_k([1, 2], rel, 2), 1.0)
        self.assertLess(ndcg_at_k([2, 1], rel, 2), 1.0)
        self.assertEqual(ndcg_at_k([1], {}, 3), 0.0)

    def test_evaluate_means(self):
        _, means = evaluate(lambda q: [1], {"q": {1: 1}}, k=1)
        self.assertEqual(means["RR"], 1.0)


if __name__ == "__main__":
    unittest.main()
