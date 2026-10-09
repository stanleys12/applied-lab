"""Market-microstructure analytics over an OrderBook and its trade tape."""


def spread(book):
    bid, ask = book.best_bid(), book.best_ask()
    return None if bid is None or ask is None else ask - bid


def midprice(book):
    bid, ask = book.best_bid(), book.best_ask()
    return None if bid is None or ask is None else (bid + ask) / 2


def vwap(trades):
    """Volume-weighted average trade price, or None for an empty tape."""
    vol = sum(t.qty for t in trades)
    return sum(t.price * t.qty for t in trades) / vol if vol else None


def imbalance(book, levels=3):
    """Top-of-book depth imbalance in [-1, 1]: +1 all bids, -1 all asks."""
    bids, asks = book.depth()
    b = sum(q for _, q in bids[:levels])
    a = sum(q for _, q in asks[:levels])
    return (b - a) / (b + a) if b + a else None


def microprice(book):
    """Size-weighted mid: leans toward the side with less resting size at the touch."""
    bids, asks = book.depth()
    if not bids or not asks:
        return None
    (bp, bq), (ap, aq) = bids[0], asks[0]
    return (bp * aq + ap * bq) / (bq + aq)


def impact_cost(book, side, qty):
    """Average slippage vs. mid for a hypothetical market order, without executing it.

    Returns (avg_fill_price, slippage_ticks, filled_qty); None if the book is one-sided.
    """
    mid = midprice(book)
    if mid is None:
        return None
    bids, asks = book.depth()
    levels = asks if side == "buy" else bids
    left, cost = qty, 0
    for px, q in levels:
        take = min(left, q)
        cost += px * take
        left -= take
        if not left:
            break
    filled = qty - left
    if not filled:
        return None
    avg = cost / filled
    return avg, abs(avg - mid), filled
