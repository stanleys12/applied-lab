"""Cox-Ross-Rubinstein binomial tree pricer, from scratch (stdlib `math` only).

Prices European *and* American options by walking a recombining
binomial tree backward from expiry. American options can be exercised
early, so at each node the holder value is `max(continuation, intrinsic)`
-- European options only ever use `continuation`.

As the number of steps `n` grows, the European price converges to the
Black-Scholes closed form (`black_scholes.price`), which is the main
correctness check: this is an independent numerical method that should
agree with the analytic one in the limit.
"""

import math

from black_scholes import CALL, PUT

AMERICAN = "american"
EUROPEAN = "european"


def crr_price(S, K, T, r, sigma, option_type=CALL, exercise=AMERICAN, n=200):
    """Price an option via an n-step CRR binomial tree.

    S: spot, K: strike, T: time to expiry in years, r: risk-free rate,
    sigma: volatility, option_type: CALL or PUT, exercise: AMERICAN or
    EUROPEAN, n: number of time steps (more steps = finer tree = more
    accurate, at O(n^2) cost).
    """
    if option_type not in (CALL, PUT):
        raise ValueError(f"option_type must be {CALL!r} or {PUT!r}, got {option_type!r}")
    if exercise not in (AMERICAN, EUROPEAN):
        raise ValueError(f"exercise must be {AMERICAN!r} or {EUROPEAN!r}, got {exercise!r}")
    assert S > 0 and K > 0 and T > 0 and sigma > 0 and n >= 1

    dt = T / n
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    disc = math.exp(-r * dt)
    p = (math.exp(r * dt) - d) / (u - d)
    if not (0 < p < 1):
        raise ValueError(
            f"risk-neutral probability p={p:.4f} outside (0, 1) -- "
            f"try more steps or check r/sigma/T are sane"
        )

    def intrinsic(spot):
        return max(spot - K, 0.0) if option_type == CALL else max(K - spot, 0.0)

    # Terminal payoffs at each of the n+1 ending nodes: S * u^j * d^(n-j).
    values = [intrinsic(S * u ** j * d ** (n - j)) for j in range(n + 1)]

    # Walk backward: at step i there are i+1 nodes (j = 0..i), each the
    # discounted expectation of its two children under the risk-neutral
    # probability p. American options additionally compare against
    # immediate exercise at that node.
    for i in range(n - 1, -1, -1):
        for j in range(i + 1):
            continuation = disc * (p * values[j + 1] + (1 - p) * values[j])
            if exercise == AMERICAN:
                spot = S * u ** j * d ** (i - j)
                values[j] = max(continuation, intrinsic(spot))
            else:
                values[j] = continuation

    return values[0]


def _demo():
    from black_scholes import price as bs_price

    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20

    print("European CRR tree vs. Black-Scholes closed form, at increasing step counts:")
    bs_call = bs_price(S, K, T, r, sigma, CALL)
    for n in (10, 50, 200, 1000):
        tree_call = crr_price(S, K, T, r, sigma, CALL, EUROPEAN, n)
        print(f"  n={n:5d}  tree={tree_call:.4f}  bs={bs_call:.4f}  diff={tree_call - bs_call:+.4f}")
    assert math.isclose(
        crr_price(S, K, T, r, sigma, CALL, EUROPEAN, 1000), bs_call, abs_tol=0.01
    )

    # American calls on a non-dividend-paying stock are never exercised
    # early (holding the call is always at least as good as exercising
    # it), so American and European call prices should match.
    american_call = crr_price(S, K, T, r, sigma, CALL, AMERICAN, 200)
    european_call = crr_price(S, K, T, r, sigma, CALL, EUROPEAN, 200)
    print(f"\n  American call = {american_call:.4f}, European call = {european_call:.4f} (expect ~equal)")
    assert math.isclose(american_call, european_call, abs_tol=1e-6)

    # American puts *can* be worth exercising early (locking in the
    # strike now beats waiting, if deep enough ITM), so the American put
    # should be worth strictly more than the European one.
    american_put = crr_price(S, K, T, r, sigma, PUT, AMERICAN, 200)
    european_put = crr_price(S, K, T, r, sigma, PUT, EUROPEAN, 200)
    print(f"  American put  = {american_put:.4f}, European put  = {european_put:.4f} (expect American >= European)")
    assert american_put >= european_put - 1e-9

    print("\nall sanity checks passed")


if __name__ == "__main__":
    _demo()
