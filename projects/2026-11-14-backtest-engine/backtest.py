"""backtest-engine: a tiny event-free, vectorless backtester (stdlib only).

Generates a synthetic price series (geometric Brownian motion, seeded), runs a strategy that
emits a target position in {-1, 0, +1} per bar, and reports equity-curve metrics.

Look-ahead safety: the signal computed from prices[0..t] is only traded at the t+1 return.
"""
import math
import random


def gbm_prices(n=500, s0=100.0, mu=0.08, sigma=0.2, seed=1, dt=1 / 252):
    rng = random.Random(seed)
    prices = [s0]
    for _ in range(n - 1):
        z = rng.gauss(0, 1)
        prices.append(prices[-1] * math.exp((mu - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * z))
    return prices


def sma(prices, window):
    """Simple moving average; None until `window` observations exist."""
    out, run = [], 0.0
    for i, p in enumerate(prices):
        run += p
        if i >= window:
            run -= prices[i - window]
        out.append(run / window if i >= window - 1 else None)
    return out


def sma_crossover(prices, fast=10, slow=30):
    """Long when fast SMA > slow SMA, short when below, flat until both are defined."""
    if fast >= slow:
        raise ValueError("fast window must be < slow window")
    f, s = sma(prices, fast), sma(prices, slow)
    return [0 if s[i] is None else (1 if f[i] > s[i] else -1) for i in range(len(prices))]


def buy_and_hold(prices):
    return [1] * len(prices)


def run_backtest(prices, signals, cost_bps=5.0):
    """Return per-bar strategy returns and equity curve (start 1.0).

    The position held over bar t->t+1 is signals[t] (decided at close of t). Each unit of
    position change pays cost_bps of notional.
    """
    if len(prices) != len(signals):
        raise ValueError("prices and signals must have equal length")
    rets, equity, pos_prev = [], [1.0], 0
    for t in range(len(prices) - 1):
        pos = signals[t]
        r = pos * (prices[t + 1] / prices[t] - 1) - abs(pos - pos_prev) * cost_bps / 1e4
        rets.append(r)
        equity.append(equity[-1] * (1 + r))
        pos_prev = pos
    return rets, equity


def metrics(rets, equity, periods=252):
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    sd = math.sqrt(var)
    peak, mdd = equity[0], 0.0
    for e in equity:
        peak = max(peak, e)
        mdd = min(mdd, e / peak - 1)
    return {
        "total_return": equity[-1] - 1,
        "cagr": equity[-1] ** (periods / n) - 1,
        "ann_vol": sd * math.sqrt(periods),
        "sharpe": mean / sd * math.sqrt(periods) if sd else float("nan"),
        "max_drawdown": mdd,
    }


def report(name, m):
    print("%-14s ret %7.1f%%  cagr %6.1f%%  vol %5.1f%%  sharpe %5.2f  maxDD %6.1f%%" % (
        name, m["total_return"] * 100, m["cagr"] * 100, m["ann_vol"] * 100, m["sharpe"], m["max_drawdown"] * 100))


if __name__ == "__main__":
    prices = gbm_prices(n=756, seed=42)
    for name, sig in [("buy&hold", buy_and_hold(prices)), ("sma 10/30", sma_crossover(prices))]:
        report(name, metrics(*run_backtest(prices, sig)))
