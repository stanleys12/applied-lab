# bm25-search-lab

A from-scratch search engine in stdlib Python: tokenizer, inverted index, Okapi BM25 ranking.

## Vision
Grow into a small retrieval lab: phrase/boolean queries, TF-IDF vs BM25 comparison,
an evaluation harness (precision@k, MRR, nDCG) on a labelled mini-corpus, and
simple query expansion.

## Run
    python3 bm25.py "how does momentum help gradient descent"
    python3 test_bm25.py

## Increments
1. Tokenizer + inverted index + BM25 scoring CLI over a built-in corpus (done)
