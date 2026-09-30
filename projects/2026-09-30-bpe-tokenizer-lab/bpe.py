"""Byte-level BPE tokenizer from scratch (stdlib only)."""
import argparse
import sys
from collections import Counter


def get_pair_counts(seqs):
    counts = Counter()
    for seq in seqs:
        for pair in zip(seq, seq[1:]):
            counts[pair] += 1
    return counts


def merge_seq(seq, pair, new_id):
    out, i = [], 0
    while i < len(seq):
        if i < len(seq) - 1 and seq[i] == pair[0] and seq[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return out


class BPETokenizer:
    def __init__(self):
        self.merges = {}  # (a, b) -> new id, in insertion (priority) order
        self.vocab = {i: bytes([i]) for i in range(256)}

    def train(self, text, vocab_size):
        if vocab_size < 256:
            raise ValueError("vocab_size must be >= 256")
        seqs = [list(text.encode("utf-8"))]
        for new_id in range(256, vocab_size):
            counts = get_pair_counts(seqs)
            if not counts:
                break
            # deterministic tie-break: highest count, then smallest pair
            pair = max(counts, key=lambda p: (counts[p], -p[0], -p[1]))
            if counts[pair] < 2:
                break
            seqs = [merge_seq(s, pair, new_id) for s in seqs]
            self.merges[pair] = new_id
            self.vocab[new_id] = self.vocab[pair[0]] + self.vocab[pair[1]]
        return self

    def encode(self, text):
        ids = list(text.encode("utf-8"))
        while len(ids) >= 2:
            pairs = set(zip(ids, ids[1:]))
            best = min(pairs, key=lambda p: self.merges.get(p, float("inf")))
            if best not in self.merges:
                break
            ids = merge_seq(ids, best, self.merges[best])
        return ids

    def decode(self, ids):
        return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description="Train a byte-level BPE and round-trip text")
    ap.add_argument("corpus", help="path to training text file")
    ap.add_argument("--vocab-size", type=int, default=300)
    ap.add_argument("--text", default="the quick brown fox", help="text to encode")
    a = ap.parse_args()
    with open(a.corpus, encoding="utf-8") as f:
        corpus = f.read()
    tok = BPETokenizer().train(corpus, a.vocab_size)
    ids = tok.encode(a.text)
    print(f"merges learned: {len(tok.merges)}")
    print(f"ids: {ids}")
    print(f"tokens: {[tok.vocab[i].decode('utf-8', 'replace') for i in ids]}")
    print(f"bytes {len(a.text.encode())} -> tokens {len(ids)}")
    assert tok.decode(ids) == a.text
    print("round-trip OK")


if __name__ == "__main__":
    sys.exit(main())
