import os
import tempfile
import unittest

from bpe import BPETokenizer, evaluate, sweep

CORPUS = "the quick brown fox jumps over the lazy dog. " * 20


class BPETests(unittest.TestCase):
    def setUp(self):
        self.tok = BPETokenizer().train(CORPUS, 300)

    def test_roundtrip_ascii_and_unicode(self):
        for text in ["the lazy fox", "", "héllo wörld ✓ 日本語", "unseen zzzz"]:
            self.assertEqual(self.tok.decode(self.tok.encode(text)), text)

    def test_compresses_training_text(self):
        self.assertLess(len(self.tok.encode(CORPUS)), len(CORPUS.encode()) / 3)

    def test_train_is_deterministic(self):
        other = BPETokenizer().train(CORPUS, 300)
        self.assertEqual(list(self.tok.merges.items()), list(other.merges.items()))

    def test_stops_when_no_repeated_pairs(self):
        tok = BPETokenizer().train("abcdefg", 400)
        self.assertEqual(len(tok.merges), 0)

    def test_save_load_equivalent(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tok.json")
            self.tok.save(path)
            loaded = BPETokenizer.load(path)
        text = "the quick brown dog"
        self.assertEqual(loaded.encode(text), self.tok.encode(text))
        self.assertEqual(loaded.vocab, self.tok.vocab)

    def test_special_tokens_atomic_and_roundtrip(self):
        self.tok.add_special_tokens(["<|endoftext|>", "<|pad|>"])
        eot = self.tok.special["<|endoftext|>"]
        text = "the dog<|endoftext|>the fox<|pad|>"
        ids = self.tok.encode(text)
        self.assertEqual(ids.count(eot), 1)
        self.assertEqual(ids[-1], self.tok.special["<|pad|>"])
        self.assertEqual(self.tok.decode(ids), text)

    def test_special_tokens_persist(self):
        self.tok.add_special_tokens(["<|endoftext|>"])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.json")
            self.tok.save(p)
            loaded = BPETokenizer.load(p)
        s = "a<|endoftext|>b"
        self.assertEqual(loaded.encode(s), self.tok.encode(s))

    def test_empty_special_rejected(self):
        with self.assertRaises(ValueError):
            self.tok.add_special_tokens([""])

    def test_evaluate_stats(self):
        st = evaluate(self.tok, CORPUS)
        self.assertEqual(st["bytes"], len(CORPUS))
        self.assertTrue(st["roundtrip"])
        self.assertGreater(st["bytes_per_token"], 1.0)
        self.assertEqual(evaluate(self.tok, "")["bytes_per_token"], 0.0)

    def test_sweep_monotonic_on_train_text(self):
        rows = sweep(CORPUS, CORPUS, [256, 270, 300])
        ratios = [r[2]["bytes_per_token"] for r in rows]
        self.assertEqual(ratios[0], 1.0)
        self.assertEqual(ratios, sorted(ratios))

    def test_small_vocab_rejected(self):
        with self.assertRaises(ValueError):
            BPETokenizer().train("aa", 100)


if __name__ == "__main__":
    unittest.main()
