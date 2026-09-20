"""Monte Carlo option pricer, from scratch (stdlib `random`/`math` only).

Simulates terminal stock prices under geometric Brownian motion (the
same lognormal assumption Black-Scholes makes), averages the
discounted payoff across paths, and reports a standard error so the
result comes with an honest confidence interval instead of a bare
number. As path count grows, both the price and its uncertainty should
shrink toward the closed-form Black-Scholes value.
"""

import math
import random

from black_scholes import CALL, PUT


def mc_price(S, K, T, r, sigma, option_type=CALL, n_paths=20000, antithetic=True, seed=None):
    """Estimate an option's price by simulating GBM terminal prices.

    Returns (price, stderr): the Monte Carlo estimate and its standard
    error (68% confidence interval is price +/- stderr).

    Each path draws Z ~ N(0, 1) and sets
        S_T = S * exp((r - sigma^2/2) * T + sigma * sqrt(T) * Z)
    which is the exact (not discretized) solution to GBM at time T, so
    there's no time-stepping error -- only Monte Carlo sampling error.

    With `antithetic=True` (the default), each Z is paired with -Z.
    Averaging a path and its mirror image cancels first-order sampling
    noise, roughly halving the number of *independent* draws needed for
    the same standard error -- a standard variance-reduction trick that
    costs nothing but a sign flip.
    """
    if option_type not in (CALL, PUT):
        raise ValueError(f"option_type must be {CALL!r} or {PUT!r}, got {option_type!r}")
    assert S > 0 and K > 0 and T > 0 and sigma > 0 and n_paths >= 1

    rng = random.Random(seed)
    drift = (r - sigma ** 2 / 2) * T
    vol_sqrt_T = sigma * math.sqrt(T)
    disc = math.exp(-r * T)

    def payoff(S_T):
        return max(S_T - K, 0.0) if option_type == CALL else max(K - S_T, 0.0)

    discounted = []
    draws = (n_paths + 1) // 2 if antithetic else n_paths
    for _ in range(draws):
        z = rng.gauss(0, 1)
        discounted.append(disc * payoff(S * math.exp(drift + vol_sqrt_T * z)))
        if antithetic:
            discounted.append(disc * payoff(S * math.exp(drift - vol_sqrt_T * z)))

    n = len(discounted)
    mean = sum(discounted) / n
    variance = sum((x - mean) ** 2 for x in discounted) / (n - 1)
    stderr = math.sqrt(variance / n)
    return mean, stderr


def _demo():
    from black_scholes import price as bs_price

    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
    bs_call = bs_price(S, K, T, r, sigma, CALL)

    print("Monte Carlo call price vs. Black-Scholes, at increasing path counts:")
    for n_paths in (1000, 10000, 100000):
        mc, se = mc_price(S, K, T, r, sigma, CALL, n_paths=n_paths, seed=42)
        within = "yes" if abs(mc - bs_call) <= 3 * se else "no"
        print(
            f"  n_paths={n_paths:7d}  mc={mc:.4f} +/- {se:.4f}  "
            f"bs={bs_call:.4f}  within 3*stderr={within}"
        )

    mc, se = mc_price(S, K, T, r, sigma, CALL, n_paths=200000, seed=42)
    assert abs(mc - bs_call) <= 4 * se, "MC estimate should land within a few standard errors of BS"

    # Antithetic variates should reduce variance vs. plain sampling at
    # the same path count -- check the standard error is smaller.
    _, se_plain = mc_price(S, K, T, r, sigma, CALL, n_paths=20000, antithetic=False, seed=7)
    _, se_anti = mc_price(S, K, T, r, sigma, CALL, n_paths=20000, antithetic=True, seed=7)
    print(f"\n  stderr plain sampling     = {se_plain:.5f}")
    print(f"  stderr antithetic sampling = {se_anti:.5f} (expect smaller)")
    assert se_anti < se_plain

    print("\nall sanity checks passed")


if __name__ == "__main__":
    _demo()
