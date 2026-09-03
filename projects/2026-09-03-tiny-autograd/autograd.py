"""A scalar-valued automatic differentiation engine, built from scratch.

Every arithmetic operation on a Value records how it was produced (its
"children" and a local backward rule). Value.backward() then walks the
expression graph in reverse topological order, applying the chain rule
at each node, so d(output)/d(every input) falls out automatically.

This is the same idea behind PyTorch's autograd, minus the tensors,
GPU kernels, and everything else that makes it fast.
"""

import math


class Value:
    def __init__(self, data, _children=(), _op=""):
        self.data = data
        self.grad = 0.0
        self._backward = lambda: None
        self._prev = set(_children)
        self._op = _op

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            self.grad += out.grad
            other.grad += out.grad

        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad

        out._backward = _backward
        return out

    def __pow__(self, power):
        assert isinstance(power, (int, float)), "only int/float powers supported"
        out = Value(self.data ** power, (self,), f"**{power}")

        def _backward():
            self.grad += (power * self.data ** (power - 1)) * out.grad

        out._backward = _backward
        return out

    def tanh(self):
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward():
            self.grad += (1 - t ** 2) * out.grad

        out._backward = _backward
        return out

    def relu(self):
        out = Value(max(0.0, self.data), (self,), "relu")

        def _backward():
            self.grad += (out.data > 0) * out.grad

        out._backward = _backward
        return out

    def backward(self):
        topo = []
        visited = set()

        def build(v):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build(child)
                topo.append(v)

        build(self)

        self.grad = 1.0
        for v in reversed(topo):
            v._backward()

    def __neg__(self):
        return self * -1

    def __sub__(self, other):
        return self + (-other if isinstance(other, Value) else -Value(other))

    def __rsub__(self, other):
        return Value(other) - self

    def __radd__(self, other):
        return self + other

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return self * other ** -1

    def __rtruediv__(self, other):
        return Value(other) / self

    def __repr__(self):
        return f"Value(data={self.data:.4f}, grad={self.grad:.4f})"


def _demo():
    # f(a, b) = (a * b + b**3) tanh'd — check the gradients by hand:
    # df/da = tanh'(z) * b, df/db = tanh'(z) * (a + 3*b**2), where z = a*b + b**3
    a = Value(0.5)
    b = Value(-1.0)
    z = a * b + b ** 3
    f = z.tanh()
    f.backward()

    dz = 1 - math.tanh(z.data) ** 2
    expected_da = dz * b.data
    expected_db = dz * (a.data + 3 * b.data ** 2)

    print(f"f = {f.data:.6f}")
    print(f"df/da = {a.grad:.6f} (expected {expected_da:.6f})")
    print(f"df/db = {b.grad:.6f} (expected {expected_db:.6f})")
    assert math.isclose(a.grad, expected_da, abs_tol=1e-9)
    assert math.isclose(b.grad, expected_db, abs_tol=1e-9)
    print("gradients match closed-form derivatives")


if __name__ == "__main__":
    _demo()
