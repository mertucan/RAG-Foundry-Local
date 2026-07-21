import unittest

from app.chunker import chunk_text, cosine_similarity, parse_front_matter, term_frequency


class ChunkerTests(unittest.TestCase):
    def test_parse_front_matter(self):
        meta, body = parse_front_matter("---\ntitle: Demo\ncategory: Test\n---\n# Body")
        self.assertEqual(meta["title"], "Demo")
        self.assertEqual(body.strip(), "# Body")

    def test_chunk_text_overlap(self):
        text = " ".join(f"w{i}" for i in range(20))
        chunks = chunk_text(text, max_tokens=10, overlap_tokens=2)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[1].startswith("w8"))

    def test_term_frequency_and_similarity(self):
        a = term_frequency("Gas leak gas detector")
        b = term_frequency("gas detector")
        self.assertEqual(a["gas"], 2)
        self.assertGreater(cosine_similarity(a, b), 0)


if __name__ == "__main__":
    unittest.main()
