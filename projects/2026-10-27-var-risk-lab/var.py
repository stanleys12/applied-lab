"""Value-at-Risk lab: historical and parametric (normal) VaR / CVaR on a return series (stdlib only)."""
import math
import random
import sys
from statistics import NormalDist, mean, stdev


def synthetic_returns(n=750, mu=0.0004, sigma=0.01, seed=7):
    """Fat-tailed daily returns: normal body plus occasional 3x-vol shock days."""
    rng = random.Random(seed)
    return [rng.gauss(mu, sigma * (3 if rng.random() < 0.03 else 1)) for _ in range(n)]


def historical_var(returns, alpha=0.99):
    """Loss (positive number) exceeded on only (1-alpha) of days, from the empirical distribution."""
    if not returns:
        raise ValueError("empty return series")
    losses = sorted(-r for r in returns)
    idx = min(len(losses) - 1, math.ceil(alpha * len(losses)) - 1)
    return max(losses[idx], 0.0)


def historical_cvar(returns, alpha=0.99):
    """Expected shortfall: mean loss on days at or beyond the VaR threshold."""
    var = historical_var(returns, alpha)
    tail = [-r for r in returns if -r >= var]
    return mean(tail)


def parametric_var(returns, alpha=0.99):
    """Variance-covariance VaR assuming normally distributed returns."""
    z = NormalDist().inv_cdf(alpha)
    return max(-mean(returns) + z * stdev(returns), 0.0)


def parametric_cvar(returns, alpha=0.99):
    nd = NormalDist()
    z = nd.inv_cdf(alpha)
    return -mean(returns) + stdev(returns) * nd.pdf(z) / (1 - alpha)


def excess_kurtosis(returns):
    m, n = mean(returns), len(returns)
    var = sum((r - m) ** 2 for r in returns) / n
    return sum((r - m) ** 4 for r in returns) / n / var ** 2 - 3


def monte_carlo_losses(returns, n_sims=20000, dist="normal", seed=1):
    """Simulated one-day losses from a distribution fitted to `returns`.
    dist="normal": Gaussian. dist="t": Student-t with df moment-matched to the sample excess
    kurtosis (df = 4 + 6/k, clamped to [4.5, 60]) and scaled to the sample stdev."""
    rng = random.Random(seed)
    mu, sd = mean(returns), stdev(returns)
    if dist == "normal":
        return [-rng.gauss(mu, sd) for _ in range(n_sims)]
    if dist != "t":
        raise ValueError(f"unknown dist {dist!r}")
    k = excess_kurtosis(returns)
    df = 60.0 if k <= 0.1 else min(60.0, max(4.5, 4 + 6 / k))
    scale = sd * math.sqrt((df - 2) / df)
    return [-(mu + scale * rng.gauss(0, 1) / math.sqrt(rng.gammavariate(df / 2, 2) / df))
            for _ in range(n_sims)]


def monte_carlo_var(returns, alpha=0.99, dist="normal", n_sims=20000, seed=1):
    """VaR and CVaR (loss tuple) from Monte Carlo simulation. Returns (var, cvar)."""
    losses = sorted(monte_carlo_losses(returns, n_sims, dist, seed))
    idx = min(len(losses) - 1, math.ceil(alpha * len(losses)) - 1)
    var = max(losses[idx], 0.0)
    return var, mean(losses[idx:])


def backtest(returns, var_fn, alpha=0.99, window=250):
    """Rolling one-day-ahead backtest: VaR from the previous `window` returns vs the realised
    return. Returns (exceedances, observations)."""
    if len(returns) <= window:
        raise ValueError("need more returns than the window")
    hits = sum(1 for t in range(window, len(returns))
               if -returns[t] > var_fn(returns[t - window:t], alpha))
    return hits, len(returns) - window


def kupiec_pof(hits, n, alpha=0.99):
    """Kupiec proportion-of-failures test. Returns (LR statistic, p-value); a small p-value
    means the exceedance rate is inconsistent with 1-alpha (chi-squared, 1 dof)."""
    p = 1 - alpha

    def ll(q):  # binomial log-likelihood, with 0*log(0) = 0
        return (n - hits) * math.log(1 - q) + (hits * math.log(q) if hits else 0.0)

    lr = max(-2 * (ll(p) - ll(hits / n)), 0.0)
    return lr, math.erfc(math.sqrt(lr / 2))


def backtest_report(returns, alpha=0.99, window=250):
    lines = [f"backtest {alpha:.0%} VaR, window={window}, expected rate {1 - alpha:.1%}"]
    for name, fn in (("historical", historical_var), ("parametric", parametric_var)):
        hits, n = backtest(returns, fn, alpha, window)
        lr, pval = kupiec_pof(hits, n, alpha)
        verdict = "REJECT" if pval < 0.05 else "ok"
        lines.append(f"  {name:10s} {hits:3d}/{n} = {hits / n:5.2%}  LR={lr:5.2f}  p={pval:.3f}  {verdict}")
    return "\n".join(lines)


def report(returns, alphas=(0.95, 0.99), notional=1_000_000):
    lines = [f"{len(returns)} daily returns, notional ${notional:,.0f}"]
    for a in alphas:
        for name, fn in (("hist VaR", historical_var), ("hist CVaR", historical_cvar),
                         ("param VaR", parametric_var), ("param CVaR", parametric_cvar)):
            v = fn(returns, a)
            lines.append(f"  {a:.0%} {name:10s} {v:7.3%}  ${v * notional:>10,.0f}")
        for dist in ("normal", "t"):
            v, c = monte_carlo_var(returns, a, dist)
            lines.append(f"  {a:.0%} MC-{dist:6s} VaR {v:7.3%}  CVaR {c:7.3%}")
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    returns = [float(x) for x in argv] if argv else synthetic_returns()
    print(report(returns))
    if len(returns) > 250:
        print(backtest_report(returns))


if __name__ == "__main__":
    main()
