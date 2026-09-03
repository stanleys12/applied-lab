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

## Neural net demo

```bash
python3 nn.py
```

`nn.py` builds `Neuron` / `Layer` / `MLP` classes on top of `Value` and
trains a 2-16-16-1 MLP (tanh hidden units) on a toy 2D dataset — four
clusters arranged so the two classes are not linearly separable, forcing
the hidden layers to actually do something. Training uses hinge loss
plus a small L2 term, plain SGD with a linearly decaying learning rate,
and manual `backward()` / gradient-descent steps (no optimizer class
yet):

```
epoch   0  loss 1.3639  accuracy 50.00%
epoch  50  loss 0.0117  accuracy 100.00%
...
final accuracy: 80/80 = 100.00%
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

A gradient-checking suite: for each op (and a few composite/nested
expressions), it compares the analytic gradient from `.backward()`
against a central-difference numerical estimate. This catches a wrong
backward rule in a way a normal "does `.data` look right" test can't —
e.g. it verifies gradients correctly *accumulate* rather than overwrite
when a value is reused more than once in an expression (`x * x + x`).

## Current ops

`+`, `-`, `*`, `/`, `**` (int/float powers), `tanh`, `relu`, plus the
reflected forms (`__radd__`, `__rmul__`, etc.) so `Value`s mix freely
with plain numbers on either side of an operator.

## Vision / growth plan

- ~~`Neuron` / `Layer` / `MLP` classes built on top of `Value`, with a
  manual SGD training loop on a toy classification dataset~~ done
- ~~A gradient-checking test suite (finite-difference vs. analytic)~~ done

Future increments:

- More ops: `exp`, `log`, `sigmoid`
- An ASCII loss-curve printout during training
- A pluggable optimizer (SGD with momentum) instead of the raw update loop
