"""ngram-lm-lab: a from-scratch character n-gram language model (stdlib only).

Trains on text, scores held-out text with perplexity, and samples new text.
Smoothing here is add-k (Laplace-style); later increments add backoff/interpolation.
"""
import math
import random
from collections import Counter, defaultdict

BOS, EOS = "\x02", "\x03"


class NGramLM:
    def __init__(self, n=3, k=0.1):
        if n < 1:
            raise ValueError("n must be >= 1")
        self.n, self.k = n, k
        self.counts = defaultdict(Counter)   # context tuple -> Counter(next char)
        self.vocab = {EOS}

    def _padded(self, text):
        return [BOS] * (self.n - 1) + list(text) + [EOS]

    def train(self, texts):
        for text in texts:
            seq = self._padded(text)
            self.vocab.update(text)
            for i in range(self.n - 1, len(seq)):
                ctx = tuple(seq[i - self.n + 1:i])
                self.counts[ctx][seq[i]] += 1
        return self

    def prob(self, ctx, ch):
        """P(ch | ctx) with add-k smoothing over the training vocabulary (+1 for unseen chars)."""
        c = self.counts.get(tuple(ctx))
        total = sum(c.values()) if c else 0
        v = len(self.vocab) + 1  # reserve mass for an <unk> symbol
        return ((c[ch] if c else 0) + self.k) / (total + self.k * v)

    def logprob(self, text):
        seq = self._padded(text)
        lp = 0.0
        for i in range(self.n - 1, len(seq)):
            lp += math.log(self.prob(seq[i - self.n + 1:i], seq[i]))
        return lp, len(seq) - (self.n - 1)

    def perplexity(self, texts):
        lp = n = 0
        for t in texts:
            a, b = self.logprob(t)
            lp, n = lp + a, n + b
        return math.exp(-lp / n)

    def sample(self, rng=None, max_len=200):
        rng = rng or random.Random()
        ctx, out = [BOS] * (self.n - 1), []
        while len(out) < max_len:
            c = self.counts.get(tuple(ctx))
            if not c:
                break
            ch = rng.choices(list(c), weights=list(c.values()))[0]
            if ch == EOS:
                break
            out.append(ch)
            ctx = (ctx + [ch])[1:] if self.n > 1 else []
        return "".join(out)


CORPUS = [
    "the quick brown fox jumps over the lazy dog",
    "a journey of a thousand miles begins with a single step",
    "to be or not to be that is the question",
    "all that glitters is not gold",
    "the early bird catches the worm",
    "actions speak louder than words",
    "better late than never",
    "every cloud has a silver lining",
    "fortune favors the bold",
    "knowledge is power",
    "practice makes perfect",
    "the pen is mightier than the sword",
    "time and tide wait for no man",
    "where there is a will there is a way",
    "a stitch in time saves nine",
]

if __name__ == "__main__":
    train, test = CORPUS[:-4], CORPUS[-4:]
    print("held-out perplexity by order (add-k=0.1):")
    for n in range(1, 6):
        lm = NGramLM(n).train(train)
        print("  n=%d  ppl=%.2f" % (n, lm.perplexity(test)))
    lm = NGramLM(3).train(CORPUS)
    rng = random.Random(7)
    print("samples (n=3):")
    for _ in range(4):
        print("  " + lm.sample(rng))
