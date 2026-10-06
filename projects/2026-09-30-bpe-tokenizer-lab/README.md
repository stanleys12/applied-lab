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
    python3 bpe.py --load tok.json --special '<|endoftext|>' --text 'the fox<|endoftext|>'
    python3 bpe.py --load tok.json --eval sample.txt
    python3 bpe.py sample.txt --eval sample.txt --sweep 256 270 290 320
    python3 bpe.py sample.txt --vocab-size 290 --pretokenize --save tok_pre.json
    python3 test_bpe.py

## Increments
1. Core byte-level BPE: train, encode, decode, CLI (done)
2. JSON save/load of merges (`--save` / `--load`) + unittest suite (done)
3. Special tokens (`add_special_tokens`, `--special`): atomic ids, persisted in JSON (done)
4. Compression evaluation: `evaluate()`, `--eval`, and `--sweep` over vocab sizes (done)
5. GPT-2 style regex pre-tokenization (`--pretokenize`): merges never cross word/punctuation boundaries; flag persisted in JSON (done)
