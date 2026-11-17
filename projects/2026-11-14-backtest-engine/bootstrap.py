"""Bootstrap confidence intervals for the Sharpe ratio.

Uses the stationary bootstrap (Politis & Romano 1994): resample blocks of geometrically
distributed length so serial dependence in returns (e.g. from a trend-following position
held for many bars) is partly preserved. Block length 1 reduces to the iid bootstrap.
"""
import math
import random
from backtest import gbm_prices, sma_crossover, buy_and_hold, run_backtest


def sharpe(rets, periods=252):
    n = len(rets)
    mean = sum(rets) / n
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (n - 1))
    return mean / sd * math.sqrt(periods) if sd else float("nan")


def stationary_resample(rets, mean_block, rng):
    """One resampled series of the same length; wraps circularly, new block w.p. 1/mean_block."""
    n = len(rets)
    p = 1.0 / mean_block
    out, i = [], rng.randrange(n)
    for _ in range(n):
        out.append(rets[i])
        i = rng.randrange(n) if rng.random() < p else (i + 1) % n
    return out


def sharpe_ci(rets, n_boot=1000, mean_block=10, alpha=0.05, seed=0):
    """Return (point, lo, hi, p_le_zero): percentile CI and share of resamples with Sharpe <= 0."""
    rng = random.Random(seed)
    dist = sorted(sharpe(stationary_resample(rets, mean_block, rng)) for _ in range(n_boot))
    lo = dist[int(alpha / 2 * n_boot)]
    hi = dist[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    p0 = sum(d <= 0 for d in dist) / n_boot
    return sharpe(rets), lo, hi, p0


if __name__ == "__main__":
    prices = gbm_prices(n=756, seed=42)
    for name, sig in [("buy&hold", buy_and_hold(prices)), ("sma 10/30", sma_crossover(prices))]:
        rets, _ = run_backtest(prices, sig)
        pt, lo, hi, p0 = sharpe_ci(rets)
        print("%-10s sharpe %5.2f  95%% CI [%5.2f, %5.2f]  P(sharpe<=0) %.2f" % (name, pt, lo, hi, p0))
    # Sanity: CI width shrinks roughly like 1/sqrt(years) -- 3y vs 12y of the same process.
    for n in (756, 3024):
        r, _ = run_backtest(*(lambda p: (p, buy_and_hold(p)))(gbm_prices(n=n, seed=7)))
        pt, lo, hi, _ = sharpe_ci(r)
        print("n=%4d  sharpe %5.2f  CI width %.2f" % (n, pt, hi - lo))
