# ngram-lm-lab

A from-scratch character n-gram language model, stdlib only. The goal is to build up the
classic LM toolkit by hand and see *why* each piece matters via perplexity numbers.

## Vision
Count-based LM -> smoothing comparison -> backoff/interpolation -> evaluation harness
(train/test split, perplexity curves) -> tiny CLI for training on a file and sampling.

## Run
    python3 ngram_lm.py

## Increments
1. N-gram counts, add-k smoothing, perplexity, sampling, demo over a tiny corpus (done)
