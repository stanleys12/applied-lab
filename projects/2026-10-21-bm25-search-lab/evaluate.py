"""Retrieval evaluation harness: precision@k, reciprocal rank, nDCG@k over labelled queries."""
import math

from bm25 import CORPUS, Index

# query -> {doc_id: graded relevance (1 = relevant, 2 = highly relevant)}
QRELS = {
    "gradient descent": {0: 2, 7: 2, 1: 1},
    "momentum velocity": {7: 2, 0: 1},
    "loss gradients weights": {1: 2, 0: 1},
    "subword vocabulary": {2: 2},
    "limit orders price": {3: 2},
    "option volatility expiry": {4: 2},
    "browser scripts policy": {5: 2},
    "attention tokens sequence": {6: 2},
}


def precision_at_k(ranked, rel, k):
    return sum(1 for d in ranked[:k] if rel.get(d, 0) > 0) / k


def reciprocal_rank(ranked, rel):
    for i, d in enumerate(ranked, 1):
        if rel.get(d, 0) > 0:
            return 1 / i
    return 0.0


def ndcg_at_k(ranked, rel, k):
    dcg = sum(rel.get(d, 0) / math.log2(i + 1) for i, d in enumerate(ranked[:k], 1))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 1) for i, g in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def evaluate(search, qrels=QRELS, k=3):
    """search(query) -> ranked list of doc ids. Returns per-query rows and macro means."""
    rows = {}
    for q, rel in qrels.items():
        ranked = search(q)
        rows[q] = {f"P@{k}": precision_at_k(ranked, rel, k),
                   "RR": reciprocal_rank(ranked, rel),
                   f"nDCG@{k}": ndcg_at_k(ranked, rel, k)}
    metrics = next(iter(rows.values())).keys()
    means = {m: sum(r[m] for r in rows.values()) / len(rows) for m in metrics}
    return rows, means


def main():
    idx = Index()
    for doc in CORPUS:
        idx.add(doc)
    for scorer in ("bm25", "tfidf"):
        rows, means = evaluate(lambda q: [d for d, _ in idx.search(q, top_k=10, scorer=scorer)])
        print(f"== {scorer} ==")
        for q, r in rows.items():
            print(f"{q:28s} " + "  ".join(f"{m}={v:.2f}" for m, v in r.items()))
        print(f"{'MEAN':28s} " + "  ".join(f"{m}={v:.2f}" for m, v in means.items()))


if __name__ == "__main__":
    main()
