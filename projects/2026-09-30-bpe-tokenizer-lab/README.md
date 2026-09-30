# bpe-tokenizer-lab

Byte-level Byte-Pair Encoding tokenizer built from scratch (stdlib only).

## Vision
Grow from a minimal trainer/encoder into a small tokenizer toolkit: save/load,
special tokens, a test suite, and compression-ratio evaluation.

## Run
    python3 bpe.py sample.txt --vocab-size 290 --text "the quick brown fox"

Save and reuse a trained tokenizer, then run the tests:

    python3 bpe.py sample.txt --vocab-size 290 --save tok.json
    python3 bpe.py --load tok.json --text "lazy dog"
    python3 test_bpe.py

## Increments
1. Core byte-level BPE: train, encode, decode, CLI (done)
2. JSON save/load of merges (`--save` / `--load`) + unittest suite (done)
