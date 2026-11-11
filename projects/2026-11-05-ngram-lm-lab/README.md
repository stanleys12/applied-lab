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
2. Jelinek-Mercer interpolated LM (`InterpolatedLM`): mixes all context orders, stable at high n (n=5 ppl 12.9 vs 24.2 add-k) (done)
3. `InterpolatedLM.fit_lambdas`: EM-fitted mixing weights on a dev split (n=4 test ppl 12.3 -> 10.3); `components()` refactor, cache invalidated on retrain (done)
4. `KneserNeyLM`: interpolated Kneser-Ney (absolute discount, continuation counts); distributions sum to 1 over vocab+unk; best result n=2 ppl 10.55 vs add-k 11.73 (done)
