# tiny-autograd

A scalar-valued reverse-mode automatic differentiation engine, built
from scratch — no numpy, no frameworks. `Value` wraps a number and
records every operation applied to it as a small expression graph;
calling `.backward()` walks that graph in reverse topological order and
applies the chain rule, so every gradient falls out automatically.

## Why

Backprop feels like magic until you've built it. This project makes the
mechanism visible: ~120 lines that implement `+`, `*`, `**`, `tanh`,
`relu`, and topological-sort-based `backward()`. Everything an ML
framework does under the hood, spelled out.

## Run it

```bash
python3 autograd.py
```

This runs a self-check demo: builds `f = tanh(a*b + b**3)`, calls
`.backward()`, and asserts the resulting gradients match the closed-form
derivative computed by hand.

```
f = -0.905148
df/da = -0.180707 (expected -0.180707)
df/db = 0.632473 (expected 0.632473)
gradients match closed-form derivatives
```

## Current ops

`+`, `-`, `*`, `/`, `**` (int/float powers), `tanh`, `relu`, plus the
reflected forms (`__radd__`, `__rmul__`, etc.) so `Value`s mix freely
with plain numbers on either side of an operator.

## Vision / growth plan

This is the first slice — a bare autograd core. Future increments:

- `Neuron` / `Layer` / `MLP` classes built on top of `Value`, with a
  manual SGD training loop on a toy classification dataset
- More ops: `exp`, `log`, `sigmoid`
- A gradient-checking test suite (finite-difference vs. analytic)
- An ASCII loss-curve printout during training
- L2 regularization / weight decay
- A second optimizer (SGD with momentum) for comparison
