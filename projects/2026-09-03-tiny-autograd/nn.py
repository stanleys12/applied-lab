"""A tiny multi-layer perceptron built on top of the autograd `Value` engine.

Neuron -> Layer -> MLP, each a thin wrapper around Value operations, so
forward pass, loss, and backward pass all share the same expression-graph
machinery from autograd.py. Includes a training demo on a toy 2D binary
classification dataset (two interleaving clusters), trained with plain
SGD and no framework in sight.
"""

import random

from autograd import Value


class Neuron:
    def __init__(self, n_in, nonlin=True):
        self.w = [Value(random.uniform(-1, 1)) for _ in range(n_in)]
        self.b = Value(0.0)
        self.nonlin = nonlin

    def __call__(self, x):
        act = sum((wi * xi for wi, xi in zip(self.w, x)), self.b)
        return act.tanh() if self.nonlin else act

    def parameters(self):
        return self.w + [self.b]


class Layer:
    def __init__(self, n_in, n_out, **kwargs):
        self.neurons = [Neuron(n_in, **kwargs) for _ in range(n_out)]

    def __call__(self, x):
        out = [n(x) for n in self.neurons]
        return out[0] if len(out) == 1 else out

    def parameters(self):
        return [p for n in self.neurons for p in n.parameters()]


class MLP:
    def __init__(self, n_in, layer_sizes):
        sizes = [n_in] + layer_sizes
        self.layers = [
            Layer(sizes[i], sizes[i + 1], nonlin=(i != len(layer_sizes) - 1))
            for i in range(len(layer_sizes))
        ]

    def __call__(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

    def parameters(self):
        return [p for layer in self.layers for p in layer.parameters()]


def _make_dataset(n_per_class=20, seed=42):
    """Two interleaving clusters on the unit square, not linearly separable
    by a single line (offset checkerboard-style), so the MLP has to
    actually use its hidden layer."""
    rng = random.Random(seed)
    xs, ys = [], []
    centers = [(-0.6, -0.6), (0.6, 0.6), (-0.6, 0.6), (0.6, -0.6)]
    labels = [1, 1, -1, -1]
    for (cx, cy), label in zip(centers, labels):
        for _ in range(n_per_class):
            xs.append((cx + rng.uniform(-0.3, 0.3), cy + rng.uniform(-0.3, 0.3)))
            ys.append(label)
    return xs, ys


def _train():
    random.seed(1)
    xs, ys = _make_dataset()
    model = MLP(2, [16, 16, 1])

    epochs = 300
    for epoch in range(epochs):
        lr = 0.1 * (1 - epoch / epochs) + 0.01  # linear decay 0.11 -> 0.01

        preds = [model(x) for x in xs]
        # hinge loss: max(0, 1 - y * pred), averaged, plus small L2 term
        losses = [(1 + -yi * pi).relu() for yi, pi in zip(ys, preds)]
        data_loss = sum(losses, Value(0.0)) / len(losses)
        reg_loss = sum((p * p for p in model.parameters()), Value(0.0)) * 1e-4
        loss = data_loss + reg_loss

        for p in model.parameters():
            p.grad = 0.0
        loss.backward()
        for p in model.parameters():
            p.data -= lr * p.grad

        if epoch % 50 == 0 or epoch == epochs - 1:
            correct = sum(
                (pi.data > 0) == (yi > 0) for pi, yi in zip(preds, ys)
            )
            acc = correct / len(ys)
            print(f"epoch {epoch:3d}  loss {loss.data:.4f}  accuracy {acc:.2%}")

    preds = [model(x) for x in xs]
    correct = sum((pi.data > 0) == (yi > 0) for pi, yi in zip(preds, ys))
    print(f"final accuracy: {correct}/{len(ys)} = {correct / len(ys):.2%}")
    assert correct / len(ys) >= 0.9, "MLP failed to fit the toy dataset"


if __name__ == "__main__":
    _train()
