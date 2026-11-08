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


class InterpolatedLM(NGramLM):
    """Jelinek-Mercer interpolation: P = sum_j lam_j * P_ML(ch | last j chars), j=0..n-1.

    Order 0 is a uniform floor (add-k unigram) so unseen characters never get zero mass.
    lambdas: n weights for orders n-1..0 (default: geometric, favouring longer contexts).
    """

    def __init__(self, n=3, k=0.1, lambdas=None):
        super().__init__(n, k)
        if lambdas is None:
            w = [2.0 ** j for j in range(n)]      # longest context gets the biggest weight
            lambdas = [x / sum(w) for x in reversed(w)][::-1]
        if len(lambdas) != n or abs(sum(lambdas) - 1) > 1e-9 or min(lambdas) < 0:
            raise ValueError("need %d non-negative lambdas summing to 1" % n)
        self.lambdas = lambdas  # lambdas[j] weights the context of length j

    def prob(self, ctx, ch):
        ctx = tuple(ctx)
        v = len(self.vocab) + 1
        p = 0.0
        for j, lam in enumerate(self.lambdas):
            sub = ctx[len(ctx) - j:] if j else ()
            c = self.counts_for(sub)
            total = sum(c.values()) if c else 0
            if j == 0:
                p += lam * ((c[ch] if c else 0) + self.k) / (total + self.k * v)
            elif total:
                p += lam * c[ch] / total
            else:  # unseen context: hand its weight to the order-0 floor
                p += lam * self._floor(ch, v)
        return p

    def _floor(self, ch, v):
        c = self.counts_for(())
        return ((c[ch] if c else 0) + self.k) / (sum(c.values()) + self.k * v)

    def counts_for(self, sub):
        """Counts of next char after a context of any length <= n-1 (marginalised lazily, cached)."""
        cache = self.__dict__.setdefault("_cache", {})
        if sub not in cache:
            agg = Counter()
            m = self.n - 1 - len(sub)
            for full, c in self.counts.items():
                if full[len(full) - len(sub):] == sub if sub else True:
                    agg.update(c)
            cache[sub] = agg
        return cache[sub]


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
    print("held-out perplexity, interpolated (default lambdas):")
    for n in range(1, 6):
        lm = InterpolatedLM(n).train(train)
        print("  n=%d  ppl=%.2f" % (n, lm.perplexity(test)))
    lm = NGramLM(3).train(CORPUS)
    rng = random.Random(7)
    print("samples (n=3):")
    for _ in range(4):
        print("  " + lm.sample(rng))
