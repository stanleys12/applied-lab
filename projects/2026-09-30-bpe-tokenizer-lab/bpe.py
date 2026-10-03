"""Byte-level BPE tokenizer from scratch (stdlib only)."""
import argparse
import json
import re
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
        self.special = {}  # literal string -> id, allocated after the merges

    def add_special_tokens(self, tokens):
        """Register atomic tokens like <|endoftext|>; call after training."""
        for t in tokens:
            if not t:
                raise ValueError("special token must be non-empty")
            if t in self.special:
                continue
            new_id = 256 + len(self.merges) + len(self.special)
            self.special[t] = new_id
            self.vocab[new_id] = t.encode("utf-8")
        return self

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
        """Encode text; registered special tokens map to single ids."""
        if not self.special:
            return self._encode_chunk(text)
        pat = "(" + "|".join(re.escape(t) for t in sorted(self.special, key=len, reverse=True)) + ")"
        ids = []
        for part in re.split(pat, text):
            if part in self.special:
                ids.append(self.special[part])
            elif part:
                ids.extend(self._encode_chunk(part))
        return ids

    def _encode_chunk(self, text):
        ids = list(text.encode("utf-8"))
        while len(ids) >= 2:
            pairs = set(zip(ids, ids[1:]))
            best = min(pairs, key=lambda p: self.merges.get(p, float("inf")))
            if best not in self.merges:
                break
            ids = merge_seq(ids, best, self.merges[best])
        return ids

    def save(self, path):
        """Persist merges (in priority order) as JSON."""
        data = {"version": 1, "merges": [[a, b] for a, b in self.merges],
                "special": self.special}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != 1:
            raise ValueError("unsupported tokenizer file version")
        tok = cls()
        for new_id, (a, b) in enumerate(data["merges"], start=256):
            tok.merges[(a, b)] = new_id
            tok.vocab[new_id] = tok.vocab[a] + tok.vocab[b]
        tok.add_special_tokens(data.get("special", {}))
        return tok

    def decode(self, ids):
        return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description="Train a byte-level BPE and round-trip text")
    ap.add_argument("corpus", nargs="?", help="path to training text file")
    ap.add_argument("--save", help="write trained tokenizer to this JSON file")
    ap.add_argument("--load", help="load tokenizer from JSON instead of training")
    ap.add_argument("--vocab-size", type=int, default=300)
    ap.add_argument("--special", nargs="*", default=[], help="special tokens to register, e.g. '<|endoftext|>'")
    ap.add_argument("--text", default="the quick brown fox", help="text to encode")
    a = ap.parse_args()
    if a.load:
        tok = BPETokenizer.load(a.load)
    elif a.corpus:
        with open(a.corpus, encoding="utf-8") as f:
            tok = BPETokenizer().train(f.read(), a.vocab_size)
    else:
        ap.error("provide a corpus or --load")
    tok.add_special_tokens(a.special)
    if a.save:
        tok.save(a.save)
    ids = tok.encode(a.text)
    print(f"merges learned: {len(tok.merges)}")
    print(f"ids: {ids}")
    print(f"tokens: {[tok.vocab[i].decode('utf-8', 'replace') for i in ids]}")
    print(f"bytes {len(a.text.encode())} -> tokens {len(ids)}")
    assert tok.decode(ids) == a.text
    print("round-trip OK")


if __name__ == "__main__":
    sys.exit(main())
