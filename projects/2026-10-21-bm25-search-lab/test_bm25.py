import unittest
from bm25 import Index, tokenize


class BM25Tests(unittest.TestCase):
    def test_tokenize_drops_stopwords(self):
        self.assertEqual(tokenize("The Cat, and a Hat!"), ["cat", "hat"])

    def test_rare_term_outranks_common(self):
        idx = Index()
        for t in ["apple banana", "apple cherry", "apple durian"]:
            idx.add(t)
        self.assertGreater(idx.idf("banana"), idx.idf("apple"))
        self.assertEqual(idx.search("apple banana")[0][0], 0)

    def test_length_normalisation(self):
        idx = Index()
        idx.add("python")
        idx.add("python " + "filler " * 30)
        self.assertEqual([d for d, _ in idx.search("python")], [0, 1])

    def test_tfidf_ignores_length(self):
        idx = Index()
        idx.add("python")
        idx.add("python " + "filler " * 30)
        scores = [s for _, s in idx.search("python", scorer="tfidf")]
        self.assertEqual(scores[0], scores[1])  # BM25 would separate them
        with self.assertRaises(ValueError):
            idx.search("python", scorer="nope")

    def test_no_match_and_empty(self):
        self.assertEqual(Index().search("x"), [])
        idx = Index()
        idx.add("hello world")
        self.assertEqual(idx.search("zzz"), [])


if __name__ == "__main__":
    unittest.main()
