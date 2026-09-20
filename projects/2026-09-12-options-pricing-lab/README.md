# options-pricing-lab

A from-scratch options pricing toolkit — no numpy, no scipy, just
`math`. Starts with the Black-Scholes closed-form price and Greeks for
European options, adds implied volatility solving and a binomial tree
for American options, and will grow into a Monte Carlo pricer.

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

```bash
python3 binomial_tree.py
```

Prices a European call on an n-step CRR tree at increasing `n`, showing
convergence to the Black-Scholes price, then confirms American and
European calls agree (no early exercise without dividends) while an
American put is worth strictly more than its European counterpart.

## Current capability

`black_scholes.py`:
- `price(S, K, T, r, sigma, option_type)` — European call/put fair value
- `greeks(...)` — delta, gamma, vega, theta, rho, derived analytically
  from the same `d1`/`d2` terms as the price
- `implied_vol(market_price, S, K, T, r, option_type)` — inverts
  `price()` for sigma given an observed market price, via
  Newton-Raphson (using `greeks()`'s vega) with a bisection fallback
  for when vega is too small to trust

`binomial_tree.py`:
- `crr_price(S, K, T, r, sigma, option_type, exercise, n)` — Cox-Ross-
  Rubinstein binomial tree, supports both `EUROPEAN` and `AMERICAN`
  exercise. The European tree converges to `black_scholes.price` as
  `n` grows; American adds early-exercise comparison at each node

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Three kinds of checks, none of which require trusting the formula
itself as ground truth:
- **Put-call parity** across a grid of `S`/`K`/`T`/`r`/`sigma` values —
  `C - P == S - K*e^(-rT)` must hold regardless of whether the prices
  are "correct"
- **A known textbook reference price** (Hull) to catch a formula that's
  internally consistent but simply wrong
- **Finite-difference Greeks** — each analytic Greek is just a partial
  derivative of `price()`, so central-difference on `price()` itself
  should match `greeks()` without a separately hand-derived formula to
  compare against
- **Implied vol round-trips** — pricing at a known sigma and solving
  `implied_vol()` back from that price must recover the original sigma
- **Binomial tree convergence and exercise-style relationships** — the
  European CRR tree converges to Black-Scholes as steps increase;
  American calls equal European calls (no early exercise without
  dividends) while American puts are worth at least as much as
  European puts

## Vision / growth plan

- ~~A unit test suite (put-call parity, known reference prices, Greek
  finite-difference checks against the analytic formulas)~~ done
- ~~Implied volatility solver (Newton-Raphson / bisection) that inverts
  `price()` given a market price~~ done
- ~~A binomial (CRR) tree pricer for American options, compared against
  Black-Scholes on the European case as a correctness check~~ done

Future increments:

- A simple Monte Carlo pricer (geometric Brownian motion paths) that
  converges to the closed-form price as path count grows
