"""Inventory-skewing market maker that quotes into the simulated flow and tracks PnL."""
from book import BUY, SELL


class MarketMaker:
    def __init__(self, half_spread=2, size=5, skew=0.1, max_inv=50):
        self.half, self.size, self.skew, self.max_inv = half_spread, size, skew, max_inv
        self.inventory = 0
        self.cash = 0
        self.quote_ids = set()
        self._bid_ids = set()
        self._seen = 0  # index into book.trades already processed

    def _fills(self, book):
        for t in book.trades[self._seen:]:
            if t.maker_id in self.quote_ids:  # quotes are passive, so we are always the maker
                sign = 1 if t.maker_id in self._bid_ids else -1
                self.inventory += sign * t.qty
                self.cash -= sign * t.qty * t.price
        self._seen = len(book.trades)

    def on_step(self, book):
        """Account for fills, pull stale quotes, and re-quote around a skewed fair value."""
        self._fills(book)
        for oid in self.quote_ids:
            book.cancel(oid)
        self.quote_ids, self._bid_ids = set(), set()
        bid, ask = book.best_bid(), book.best_ask()
        if bid is None or ask is None:
            return
        # long inventory -> shift quotes down to encourage selling (and vice versa)
        fair = (bid + ask) / 2 - self.skew * self.inventory
        bpx, apx = int(fair - self.half), int(fair + self.half + 0.999)
        if self.inventory < self.max_inv and bpx > 0 and bpx < ask:
            oid, _ = book.submit_limit(BUY, bpx, self.size)
            self.quote_ids.add(oid); self._bid_ids.add(oid)
        if self.inventory > -self.max_inv and apx > bid:
            oid, _ = book.submit_limit(SELL, apx, self.size)
            self.quote_ids.add(oid)

    def mark_to_market(self, book):
        """Cash plus inventory valued at the book mid (falls back to cash if one-sided)."""
        bid, ask = book.best_bid(), book.best_ask()
        mid = (bid + ask) / 2 if bid is not None and ask is not None else 0
        return self.cash + self.inventory * mid
