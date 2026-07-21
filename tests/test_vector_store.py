import tempfile
import unittest
from pathlib import Path

from app.vector_store import VectorStore


class VectorStoreTests(unittest.TestCase):
    def test_vector_store_insert_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = VectorStore(Path(tmp) / "rag.db")
            store.insert("DOC-1", "Leak", "Safety", 0, "Gas leak detector", [1.0, 0.0])
            store.insert("DOC-2", "Meter", "Equipment", 0, "Meter install", [0.0, 1.0])

            results = store.search([0.9, 0.1], top_k=1)
            self.assertEqual(results[0]["doc_id"], "DOC-1")
            self.assertEqual(store.count(), 2)
            self.assertEqual(store.list_docs()[0]["chunks"], 1)
            store.close()


if __name__ == "__main__":
    unittest.main()
