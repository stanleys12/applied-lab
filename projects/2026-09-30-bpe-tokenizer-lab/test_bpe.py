import os
import tempfile
import unittest

from bpe import BPETokenizer

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

    def test_small_vocab_rejected(self):
        with self.assertRaises(ValueError):
            BPETokenizer().train("aa", 100)


if __name__ == "__main__":
    unittest.main()
