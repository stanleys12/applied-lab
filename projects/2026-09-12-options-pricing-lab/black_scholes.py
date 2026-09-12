"""Black-Scholes European option pricing, from scratch (stdlib `math` only).

Prices calls and puts under the standard Black-Scholes assumptions
(constant volatility, no dividends, continuous trading, log-normal
underlying) and computes the five standard Greeks by differentiating
the closed-form price with respect to each input.
"""

import math

CALL = "call"
PUT = "put"


def _norm_pdf(x):
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def _norm_cdf(x):
    return (1 + math.erf(x / math.sqrt(2))) / 2


def _d1_d2(S, K, T, r, sigma):
    assert S > 0 and K > 0 and T > 0 and sigma > 0, "S, K, T, sigma must be positive"
    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def price(S, K, T, r, sigma, option_type=CALL):
    """Fair value of a European option.

    S: spot price, K: strike, T: time to expiry in years,
    r: risk-free rate (annualized, continuously compounded),
    sigma: volatility (annualized stdev of log returns).
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    if option_type == CALL:
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    elif option_type == PUT:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
    raise ValueError(f"option_type must be {CALL!r} or {PUT!r}, got {option_type!r}")


def greeks(S, K, T, r, sigma, option_type=CALL):
    """Delta, gamma, vega, theta, rho at the given inputs.

    Gamma and vega are the same for calls and puts; delta, theta, and
    rho differ by sign/term via put-call parity.
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    pdf_d1 = _norm_pdf(d1)
    sqrt_T = math.sqrt(T)

    gamma = pdf_d1 / (S * sigma * sqrt_T)
    vega = S * pdf_d1 * sqrt_T  # per unit change in sigma (not per 1%)

    if option_type == CALL:
        delta = _norm_cdf(d1)
        theta = (
            -S * pdf_d1 * sigma / (2 * sqrt_T)
            - r * K * math.exp(-r * T) * _norm_cdf(d2)
        )
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2)
    elif option_type == PUT:
        delta = _norm_cdf(d1) - 1
        theta = (
            -S * pdf_d1 * sigma / (2 * sqrt_T)
            + r * K * math.exp(-r * T) * _norm_cdf(-d2)
        )
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2)
    else:
        raise ValueError(f"option_type must be {CALL!r} or {PUT!r}, got {option_type!r}")

    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}


def _demo():
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20

    call = price(S, K, T, r, sigma, CALL)
    put = price(S, K, T, r, sigma, PUT)
    print(f"at-the-money, S=K={S}, T={T}y, r={r:.0%}, sigma={sigma:.0%}")
    print(f"  call price = {call:.4f}")
    print(f"  put  price = {put:.4f}")

    # Put-call parity: C - P == S - K*exp(-rT). This must hold exactly
    # (up to float error) since both prices come from the same d1/d2 --
    # a cheap correctness check that doesn't require an external oracle.
    parity_lhs = call - put
    parity_rhs = S - K * math.exp(-r * T)
    print(f"  put-call parity: C-P = {parity_lhs:.6f}, S-K*e^(-rT) = {parity_rhs:.6f}")
    assert math.isclose(parity_lhs, parity_rhs, abs_tol=1e-9)

    print("\n  Greeks (call):")
    for name, value in greeks(S, K, T, r, sigma, CALL).items():
        print(f"    {name:6s} = {value:+.4f}")

    print("\n  Greeks (put):")
    for name, value in greeks(S, K, T, r, sigma, PUT).items():
        print(f"    {name:6s} = {value:+.4f}")

    # Sanity: deep ITM call should have delta close to 1, deep OTM close to 0.
    deep_itm_delta = greeks(S=200.0, K=100.0, T=T, r=r, sigma=sigma, option_type=CALL)["delta"]
    deep_otm_delta = greeks(S=50.0, K=100.0, T=T, r=r, sigma=sigma, option_type=CALL)["delta"]
    print(f"\n  deep ITM call delta = {deep_itm_delta:.4f} (expect ~1)")
    print(f"  deep OTM call delta = {deep_otm_delta:.4f} (expect ~0)")
    assert deep_itm_delta > 0.95
    assert deep_otm_delta < 0.05
    print("\nall sanity checks passed")


if __name__ == "__main__":
    _demo()
