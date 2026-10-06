"""Limit order book with price-time priority matching (stdlib only)."""
import heapq
import itertools
from dataclasses import dataclass

BUY, SELL = "buy", "sell"


@dataclass
class Trade:
    price: int  # integer ticks avoid float rounding
    qty: int
    maker_id: int
    taker_id: int


@dataclass
class Order:
    id: int
    side: str
    price: int
    qty: int


class OrderBook:
    def __init__(self):
        self._bids = []  # heap of (-price, seq, order)
        self._asks = []  # heap of (price, seq, order)
        self._seq = itertools.count()
        self._ids = itertools.count(1)
        self.trades = []
        self._live = {}  # id -> resting order; cancelled orders are dropped lazily from heaps

    def submit_limit(self, side, price, qty):
        """Match against the opposite side, rest any remainder. Returns (order_id, trades)."""
        if side not in (BUY, SELL):
            raise ValueError(f"bad side: {side!r}")
        if price <= 0 or qty <= 0:
            raise ValueError("price and qty must be positive")
        order = Order(next(self._ids), side, price, qty)
        fills = self._match(order, price)
        if order.qty > 0:
            self._live[order.id] = order
            key = -price if side == BUY else price
            heap = self._bids if side == BUY else self._asks
            heapq.heappush(heap, (key, next(self._seq), order))
        return order.id, fills

    def submit_market(self, side, qty):
        """Take liquidity at any price; unfilled remainder is discarded (IOC). Returns (order_id, trades)."""
        if side not in (BUY, SELL):
            raise ValueError(f"bad side: {side!r}")
        if qty <= 0:
            raise ValueError("qty must be positive")
        order = Order(next(self._ids), side, 0, qty)
        return order.id, self._match(order, None)

    def cancel(self, order_id):
        """Cancel a resting order. Returns False if unknown or already filled/cancelled."""
        order = self._live.pop(order_id, None)
        if order is None:
            return False
        order.qty = 0
        return True

    def _top(self, heap):
        while heap and heap[0][2].qty == 0:
            heapq.heappop(heap)
        return heap[0][2] if heap else None

    def _match(self, taker, limit):
        book = self._asks if taker.side == BUY else self._bids
        fills = []
        while taker.qty > 0:
            maker = self._top(book)
            if maker is None:
                break
            if limit is not None:
                crosses = (maker.price <= limit) if taker.side == BUY else (maker.price >= limit)
                if not crosses:
                    break
            q = min(taker.qty, maker.qty)
            fills.append(Trade(maker.price, q, maker.id, taker.id))  # trade at resting price
            taker.qty -= q
            maker.qty -= q
            if maker.qty == 0:
                heapq.heappop(book)
                self._live.pop(maker.id, None)
        self.trades.extend(fills)
        return fills

    def best_bid(self):
        top = self._top(self._bids)
        return top.price if top else None

    def best_ask(self):
        top = self._top(self._asks)
        return top.price if top else None

    def depth(self):
        """Aggregated (price, qty) levels: bids high->low, asks low->high."""
        def agg(heap, sign):
            levels = {}
            for key, _, o in heap:
                if o.qty == 0:
                    continue
                levels[sign * key] = levels.get(sign * key, 0) + o.qty
            return levels
        bids = sorted(agg(self._bids, -1).items(), reverse=True)
        asks = sorted(agg(self._asks, 1).items())
        return bids, asks

    def render(self):
        bids, asks = self.depth()
        lines = [f"  ASK {p:>6} x {q}" for p, q in reversed(asks)]
        lines.append("  ------")
        lines += [f"  BID {p:>6} x {q}" for p, q in bids]
        return "\n".join(lines)


def demo():
    ob = OrderBook()
    for side, px, qty in [(BUY, 99, 10), (BUY, 100, 5), (SELL, 102, 8), (SELL, 101, 4)]:
        ob.submit_limit(side, px, qty)
    print("initial book:\n" + ob.render())
    _, fills = ob.submit_limit(BUY, 102, 10)  # sweeps 101 then part of 102
    print("\nbuy 10 @ 102 fills:", [(t.price, t.qty) for t in fills])
    print(ob.render())
    print(f"best bid/ask: {ob.best_bid()}/{ob.best_ask()}")


if __name__ == "__main__":
    demo()
