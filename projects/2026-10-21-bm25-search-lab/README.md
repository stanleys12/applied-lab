# bm25-search-lab

A from-scratch search engine in stdlib Python: tokenizer, inverted index, Okapi BM25 ranking.

## Vision
Grow into a small retrieval lab: phrase/boolean queries, TF-IDF vs BM25 comparison,
an evaluation harness (precision@k, MRR, nDCG) on a labelled mini-corpus, and
simple query expansion.

## Run
    python3 bm25.py "how does momentum help gradient descent"
    python3 evaluate.py
    python3 -m unittest

## Increments
1. Tokenizer + inverted index + BM25 scoring CLI over a built-in corpus (done)
2. Evaluation harness: precision@k, MRR, nDCG@k over graded qrels (`evaluate.py`) (done)
3. TF-IDF baseline scorer (`--tfidf`, `search(scorer=...)`) and side-by-side eval; the two tie on the 8-doc corpus, so a larger corpus is a good future addition (done)
4. Positional index + `"quoted phrase"` queries as hard filters (stopwords dropped before adjacency check) (done)
