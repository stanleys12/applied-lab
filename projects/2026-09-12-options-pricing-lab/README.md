# options-pricing-lab

A from-scratch options pricing toolkit — no numpy, no scipy, just
`math`. Starts with the Black-Scholes closed-form price and Greeks for
European options, and will grow into implied volatility solving,
American-option trees, and a Monte Carlo pricer.

## Why

Black-Scholes is the "hello world" of quantitative finance, but most
people only ever call it through a library. Writing the CDF, the `d1`/
`d2` terms, and each Greek by hand makes the model's assumptions and
sensitivities concrete instead of a black box.

## Run it

```bash
python3 black_scholes.py
```

Prices an at-the-money call and put (`S=K=100`, 1 year to expiry,
5% risk-free rate, 20% volatility), checks put-call parity holds
exactly (both prices come from the same `d1`/`d2`, so `C - P` must
equal `S - K*e^(-rT)` up to float error), prints all five Greeks for
both option types, and sanity-checks that a deep in-the-money call has
delta near 1 while a deep out-of-the-money call has delta near 0:

```
at-the-money, S=K=100.0, T=1.0y, r=5%, sigma=20%
  call price = 10.4506
  put  price = 5.5735
  put-call parity: C-P = 4.877058, S-K*e^(-rT) = 4.877058

  Greeks (call):
    delta  = +0.6368
    gamma  = +0.0188
    vega   = +37.5240
    theta  = -6.4140
    rho    = +53.2325
  ...
all sanity checks passed
```

## Current capability

`black_scholes.py`:
- `price(S, K, T, r, sigma, option_type)` — European call/put fair value
- `greeks(...)` — delta, gamma, vega, theta, rho, derived analytically
  from the same `d1`/`d2` terms as the price

## Vision / growth plan

Future increments:

- A unit test suite (put-call parity, known reference prices, Greek
  finite-difference checks against the analytic formulas)
- Implied volatility solver (Newton-Raphson / bisection) that inverts
  `price()` given a market price
- A binomial (CRR) tree pricer for American options, compared against
  Black-Scholes on the European case as a correctness check
- A simple Monte Carlo pricer (geometric Brownian motion paths) that
  converges to the closed-form price as path count grows
