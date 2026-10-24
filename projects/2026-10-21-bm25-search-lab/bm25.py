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
        self.positions = defaultdict(dict)  # term -> {doc_id: [token offsets]} for phrase queries

    def add(self, text):
        doc_id = len(self.docs)
        tokens = tokenize(text)
        self.docs.append(text)
        self.lengths.append(len(tokens))
        for term, tf in Counter(tokens).items():
            self.postings[term][doc_id] = tf
        for pos, term in enumerate(tokens):
            self.positions[term].setdefault(doc_id, []).append(pos)
        return doc_id

    def idf(self, term):
        n, df = len(self.docs), len(self.postings.get(term, ()))
        return math.log(1 + (n - df + 0.5) / (df + 0.5))  # always positive (Lucene variant)

    def phrase_docs(self, phrase):
        """Doc ids containing the phrase's tokens consecutively. Stopwords are dropped
        first, so "gradient of the loss" matches the adjacent tokens gradient, loss."""
        terms = tokenize(phrase)
        if not terms or any(t not in self.positions for t in terms):
            return set()
        hits = set(self.positions[terms[0]])
        for t in terms[1:]:
            hits &= set(self.positions[t])
        return {d for d in hits
                if any(all(p + i in self.positions[t][d] for i, t in enumerate(terms))
                       for p in self.positions[terms[0]][d])}

    def search(self, query, top_k=5, scorer="bm25"):
        """Rank docs; only docs containing at least one query term are scored.

        scorer="bm25" is Okapi BM25; "tfidf" is classic (1+log tf) * idf with no
        length normalisation, kept as a baseline for comparison.
        """
        if scorer not in ("bm25", "tfidf"):
            raise ValueError(f"unknown scorer {scorer!r}")
        if not self.docs:
            return []
        avg_len = sum(self.lengths) / len(self.docs) or 1.0
        # "quoted phrases" are hard filters; their terms also contribute to the ranking
        phrases = re.findall(r'"([^"]*)"', query)
        allowed = None
        for ph in phrases:
            docs = self.phrase_docs(ph)
            allowed = docs if allowed is None else allowed & docs
        query = query.replace('"', " ")
        scores = defaultdict(float)
        for term in set(tokenize(query)):
            idf = self.idf(term)
            for doc_id, tf in self.postings.get(term, {}).items():
                if scorer == "tfidf":
                    scores[doc_id] += idf * (1 + math.log(tf))
                    continue
                norm = 1 - self.b + self.b * self.lengths[doc_id] / avg_len
                scores[doc_id] += idf * tf * (self.k1 + 1) / (tf + self.k1 * norm)
        if allowed is not None:
            scores = {d: sc for d, sc in scores.items() if d in allowed}
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
    argv = list(sys.argv[1:] if argv is None else argv)
    scorer = "bm25"
    if "--tfidf" in argv:
        argv.remove("--tfidf")
        scorer = "tfidf"
    query = " ".join(argv) or "gradient descent loss"
    idx = Index()
    for doc in CORPUS:
        idx.add(doc)
    print(f"query: {query!r} ({scorer})")
    for doc_id, score in idx.search(query, scorer=scorer):
        print(f"  {score:6.3f}  [{doc_id}] {idx.docs[doc_id]}")


if __name__ == "__main__":
    main()
