"""Seeded random order-flow simulator driving an OrderBook."""
import random
import analytics as an
from marketmaker import MarketMaker
from book import BUY, SELL, OrderBook


def simulate(steps=2000, seed=0, start_mid=1000, p_market=0.15, p_cancel=0.2, max_qty=20, agent=None):
    """Generate random flow around a drifting mid. Returns (book, snapshots).

    Each snapshot is (step, best_bid, best_ask) taken after the step's event.
    Limit prices are placed at a geometric-ish offset from mid, so most
    liquidity sits near the touch; marketable limits occasionally cross.
    If `agent` is given, its on_step(book) runs after every random event.
    """
    rng = random.Random(seed)
    ob = OrderBook()
    mid = start_mid
    resting = []  # ids that may still be live (cancel() tolerates stale ones)
    snaps = []
    for step in range(steps):
        r = rng.random()
        side = rng.choice((BUY, SELL))
        qty = rng.randint(1, max_qty)
        if r < p_cancel and resting:
            ob.cancel(resting.pop(rng.randrange(len(resting))))
        elif r < p_cancel + p_market:
            ob.submit_market(side, qty)
        else:
            offset = int(rng.expovariate(1 / 3)) - 1  # -1 lets some orders cross
            px = max(1, mid - offset if side == BUY else mid + offset)
            oid, _ = ob.submit_limit(side, px, qty)
            resting.append(oid)
        if agent:
            agent.on_step(ob)
        bid, ask = ob.best_bid(), ob.best_ask()
        if bid is not None and ask is not None:
            mid = (bid + ask) // 2  # mid follows the book, giving a random walk
        snaps.append((step, bid, ask))
    return ob, snaps


def main():
    ob, snaps = simulate()
    spreads = [a - b for _, b, a in snaps if b is not None and a is not None]
    print(f"trades: {len(ob.trades)}, volume: {sum(t.qty for t in ob.trades)}")
    print(f"avg spread: {sum(spreads) / len(spreads):.2f} ticks over {len(spreads)} two-sided steps")
    print(f"last trade price: {ob.trades[-1].price}")
    print(f"VWAP: {an.vwap(ob.trades):.2f}, imbalance(3): {an.imbalance(ob):+.2f}, "
          f"microprice: {an.microprice(ob):.2f}")
    print("buy-20 impact (avg px, slippage, filled):", an.impact_cost(ob, "buy", 20))
    print("final book (top 3 levels):")
    bids, asks = ob.depth()
    print("  asks:", asks[:3], "\n  bids:", bids[:3])

    mm = MarketMaker()
    ob, _ = simulate(seed=1, agent=mm)
    print(f"market maker: inventory {mm.inventory:+d}, cash {mm.cash}, "
          f"MTM PnL {mm.mark_to_market(ob):.1f}")


if __name__ == "__main__":
    main()
