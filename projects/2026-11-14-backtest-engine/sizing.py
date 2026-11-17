"""Volatility-targeted position sizing and a look-ahead-safety self-test.

vol_target scales a {-1,0,+1} signal to leverage = target_vol / realized_vol, where realized
vol is an EWMA of squared returns known at the close of bar t (uses returns up to t only),
capped at max_leverage. run_backtest already trades signals[t] over t->t+1, so the scaled
signal stays look-ahead safe.
"""
import math
from backtest import gbm_prices, sma_crossover, run_backtest, metrics, report


def vol_target(prices, signals, target_vol=0.10, lam=0.94, max_leverage=3.0, periods=252):
    var = None
    out = []
    for t in range(len(prices)):
        if t > 0:
            r = prices[t] / prices[t - 1] - 1
            var = r * r if var is None else lam * var + (1 - lam) * r * r
        if var is None or var == 0:
            out.append(0.0)  # no vol estimate yet -> stay flat
            continue
        lev = min(max_leverage, target_vol / math.sqrt(var * periods))
        out.append(signals[t] * lev)
    return out


def check_no_lookahead(seed=3, n=300, cut=200):
    """Changing prices after `cut` must not change any position decided at or before `cut`."""
    a = gbm_prices(n=n, seed=seed)
    b = a[:cut + 1] + [p * 1.5 for p in a[cut + 1:]]
    sa = vol_target(a, sma_crossover(a))
    sb = vol_target(b, sma_crossover(b))
    assert sa[:cut + 1] == sb[:cut + 1], "look-ahead leak detected"
    return True


if __name__ == "__main__":
    print("look-ahead check passed:", check_no_lookahead())
    prices = gbm_prices(n=1500, mu=0.10, sigma=0.25, seed=11)
    raw = sma_crossover(prices)
    report("raw sma", metrics(*run_backtest(prices, raw)))
    report("vol-target 10%", metrics(*run_backtest(prices, vol_target(prices, raw))))
