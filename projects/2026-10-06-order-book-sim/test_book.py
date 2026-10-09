import unittest

from book import BUY, SELL, OrderBook


class OrderBookTests(unittest.TestCase):
    def test_price_time_priority(self):
        ob = OrderBook()
        first, _ = ob.submit_limit(SELL, 100, 5)
        second, _ = ob.submit_limit(SELL, 100, 5)
        _, fills = ob.submit_limit(BUY, 100, 7)
        self.assertEqual([(t.maker_id, t.qty) for t in fills], [(first, 5), (second, 2)])

    def test_trade_at_resting_price(self):
        ob = OrderBook()
        ob.submit_limit(SELL, 100, 5)
        _, fills = ob.submit_limit(BUY, 105, 5)
        self.assertEqual(fills[0].price, 100)

    def test_no_cross_rests(self):
        ob = OrderBook()
        ob.submit_limit(SELL, 101, 5)
        _, fills = ob.submit_limit(BUY, 100, 5)
        self.assertEqual(fills, [])
        self.assertEqual((ob.best_bid(), ob.best_ask()), (100, 101))

    def test_cancel(self):
        ob = OrderBook()
        a, _ = ob.submit_limit(BUY, 100, 5)
        ob.submit_limit(BUY, 99, 5)
        self.assertTrue(ob.cancel(a))
        self.assertFalse(ob.cancel(a))
        self.assertEqual(ob.best_bid(), 99)
        self.assertEqual(ob.depth()[0], [(99, 5)])
        _, fills = ob.submit_limit(SELL, 99, 5)
        self.assertEqual([t.price for t in fills], [99])

    def test_cancel_filled_order_is_false(self):
        ob = OrderBook()
        a, _ = ob.submit_limit(SELL, 100, 5)
        ob.submit_limit(BUY, 100, 5)
        self.assertFalse(ob.cancel(a))

    def test_market_order_sweeps_and_discards_remainder(self):
        ob = OrderBook()
        ob.submit_limit(SELL, 100, 3)
        ob.submit_limit(SELL, 105, 3)
        _, fills = ob.submit_market(BUY, 10)
        self.assertEqual([(t.price, t.qty) for t in fills], [(100, 3), (105, 3)])
        self.assertEqual(ob.depth(), ([], []))  # remainder did not rest

    def test_market_on_empty_book(self):
        _, fills = OrderBook().submit_market(SELL, 5)
        self.assertEqual(fills, [])

    def test_validation(self):
        ob = OrderBook()
        for bad in [(BUY, 0, 1), (BUY, 1, 0), ("x", 1, 1)]:
            with self.assertRaises(ValueError):
                ob.submit_limit(*bad)
        with self.assertRaises(ValueError):
            ob.submit_market(BUY, 0)


class TestSim(unittest.TestCase):
    def test_deterministic_and_never_crossed(self):
        from sim import simulate
        a, sa = simulate(steps=500, seed=7)
        b, sb = simulate(steps=500, seed=7)
        self.assertEqual(sa, sb)
        self.assertEqual(len(a.trades), len(b.trades))
        self.assertGreater(len(a.trades), 0)
        for _, bid, ask in sa:
            if bid is not None and ask is not None:
                self.assertLess(bid, ask)


if __name__ == "__main__":
    unittest.main()
