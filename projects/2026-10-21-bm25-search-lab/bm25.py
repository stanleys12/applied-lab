"""Tiny BM25 search engine: tokenizer, inverted index, Okapi BM25 ranking (stdlib only)."""
import math
import re
import sys
from collections import Counter, defaultdict

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset("a an and are as at be by for from in is it of on or that the to was with".split())


def tokenize(text):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class Index:
    def __init__(self, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = []                     # raw text per doc id
        self.lengths = []                  # token count per doc id
        self.postings = defaultdict(dict)  # term -> {doc_id: term frequency}

    def add(self, text):
        doc_id = len(self.docs)
        tokens = tokenize(text)
        self.docs.append(text)
        self.lengths.append(len(tokens))
        for term, tf in Counter(tokens).items():
            self.postings[term][doc_id] = tf
        return doc_id

    def idf(self, term):
        n, df = len(self.docs), len(self.postings.get(term, ()))
        return math.log(1 + (n - df + 0.5) / (df + 0.5))  # always positive (Lucene variant)

    def search(self, query, top_k=5):
        """Rank docs by BM25; only docs containing at least one query term are scored."""
        if not self.docs:
            return []
        avg_len = sum(self.lengths) / len(self.docs) or 1.0
        scores = defaultdict(float)
        for term in set(tokenize(query)):
            idf = self.idf(term)
            for doc_id, tf in self.postings.get(term, {}).items():
                norm = 1 - self.b + self.b * self.lengths[doc_id] / avg_len
                scores[doc_id] += idf * tf * (self.k1 + 1) / (tf + self.k1 * norm)
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:top_k]


CORPUS = [
    "Gradient descent updates parameters by following the negative gradient of the loss.",
    "Backpropagation computes gradients of a loss with respect to network weights using the chain rule.",
    "Byte pair encoding merges frequent symbol pairs to build a subword vocabulary.",
    "An order book matches buy and sell limit orders by price-time priority.",
    "The Black-Scholes model prices European options using volatility and time to expiry.",
    "A content security policy restricts which scripts a browser may execute.",
    "Transformers use attention to weigh tokens in a sequence against each other.",
    "Momentum accelerates gradient descent by accumulating a velocity of past gradients.",
]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    query = " ".join(argv) or "gradient descent loss"
    idx = Index()
    for doc in CORPUS:
        idx.add(doc)
    print(f"query: {query!r}")
    for doc_id, score in idx.search(query):
        print(f"  {score:6.3f}  [{doc_id}] {idx.docs[doc_id]}")


if __name__ == "__main__":
    main()
