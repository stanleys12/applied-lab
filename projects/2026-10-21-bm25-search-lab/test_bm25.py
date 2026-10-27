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

    def test_phrase_filter(self):
        idx = Index()
        idx.add("gradient descent is simple")
        idx.add("descent of the gradient is steep")
        self.assertEqual([d for d, _ in idx.search("gradient descent")], [0, 1])
        self.assertEqual([d for d, _ in idx.search('"gradient descent"')], [0])
        self.assertEqual(idx.search('"simple gradient" descent'), [])
        self.assertEqual(idx.search('"nonexistent phrase"'), [])

    def test_stopwords_inside_phrase(self):
        idx = Index()
        idx.add("the cost of the loss")
        self.assertEqual([d for d, _ in idx.search('"cost of loss"')], [0])

    def test_no_match_and_empty(self):
        self.assertEqual(Index().search("x"), [])
        idx = Index()
        idx.add("hello world")
        self.assertEqual(idx.search("zzz"), [])


class ExpandTests(unittest.TestCase):
    def setUp(self):
        from bm25 import CORPUS
        self.idx = Index()
        for d in CORPUS:
            self.idx.add(d)

    def test_adds_new_terms_from_top_docs(self):
        q = self.idx.expand("momentum")
        self.assertTrue(q.startswith("momentum "))
        self.assertGreater(len(q.split()), 1)
        self.assertNotIn("momentum", q.split()[1:])

    def test_expansion_pulls_in_related_doc(self):
        plain = [d for d, _ in self.idx.search("loss", top_k=10)]
        expanded = [d for d, _ in self.idx.search(self.idx.expand("loss"), top_k=10)]
        self.assertNotIn(7, plain)
        self.assertIn(7, expanded)

    def test_no_hits_returns_query(self):
        self.assertEqual(self.idx.expand("zzzz"), "zzzz")


if __name__ == "__main__":
    unittest.main()
