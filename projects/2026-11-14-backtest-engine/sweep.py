"""Parameter sweep + out-of-sample check: shows how in-sample "best" SMA params fail on noise.

Prices are driftless GBM (mu=0), so no SMA rule has a true edge. We pick the best (fast, slow)
pair on a training window by Sharpe, then evaluate that same pair on the following test window.
Averaged over many seeds, in-sample Sharpe is positive (selection bias) while out-of-sample ~ 0
(minus costs).
"""
import statistics
from backtest import gbm_prices, sma_crossover, run_backtest, metrics

FASTS = [3, 5, 8, 10, 15, 20]
SLOWS = [20, 30, 50, 80, 120]


def sweep(prices, fasts=FASTS, slows=SLOWS, cost_bps=5.0):
    """Return {(fast, slow): sharpe} over all valid grid points."""
    out = {}
    for f in fasts:
        for s in slows:
            if f >= s:
                continue
            m = metrics(*run_backtest(prices, sma_crossover(prices, f, s), cost_bps))
            out[(f, s)] = m["sharpe"]
    return out


def train_test(prices, split=0.5, cost_bps=5.0):
    """Pick best params on the first `split` fraction; return (params, in-sample Sharpe, out-of-sample Sharpe).

    Signals for the test window are computed on the full series (so SMAs are warmed up using
    train history, which is legitimate: it is all past data) and scored only from the split on.
    """
    k = int(len(prices) * split)
    grid = sweep(prices[:k], cost_bps=cost_bps)
    best = max(grid, key=grid.get)
    sig = sma_crossover(prices, *best)
    # Start at k-1 so the position decided at the last train close is the first test position.
    m = metrics(*run_backtest(prices[k - 1:], sig[k - 1:], cost_bps))
    return best, grid[best], m["sharpe"]


if __name__ == "__main__":
    ins, oos = [], []
    for seed in range(200):
        prices = gbm_prices(n=1000, mu=0.0, seed=seed)
        _, i, o = train_test(prices)
        ins.append(i)
        oos.append(o)
    print("seeds=200  driftless GBM  train/test 50/50")
    print("mean in-sample Sharpe  (best of grid): %6.2f" % statistics.mean(ins))
    print("mean out-of-sample Sharpe (same pair): %6.2f" % statistics.mean(oos))
    print("seeds where OOS < IS: %d/200" % sum(o < i for i, o in zip(ins, oos)))
