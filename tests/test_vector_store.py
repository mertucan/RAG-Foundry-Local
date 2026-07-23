import tempfile
import unittest
from pathlib import Path

from app.vector_store import VectorStore


class VectorStoreTests(unittest.TestCase):
    def test_vector_store_insert_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = VectorStore(Path(tmp) / "rag.db")
            store.insert("DOC-1", "RAG Notes", "AI Concepts", 0, "RAG retrieval notes", [1.0, 0.0])
            store.insert("DOC-2", "Meter", "Equipment", 0, "Meter install", [0.0, 1.0])

            results = store.search([0.9, 0.1], top_k=1)
            self.assertEqual(results[0]["doc_id"], "DOC-1")
            self.assertEqual(store.count(), 2)
            self.assertEqual(store.list_docs()[0]["chunks"], 1)
            store.close()

    def test_vector_store_filters_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = VectorStore(Path(tmp) / "rag.db")
            try:
                store.insert(
                    "DOC-A",
                    "RAG",
                    "AI",
                    0,
                    "# Page 2\n\nretrieval notes",
                    [1.0, 0.0],
                    filename="rag.pdf",
                    page_number=2,
                    tags="rag, retrieval",
                    course="Local AI",
                    topic="RAG",
                    semester="Summer 2026",
                    source_type="pdf",
                )
                store.insert(
                    "DOC-B",
                    "Writing",
                    "Academic",
                    0,
                    "writing notes",
                    [0.0, 1.0],
                    tags="writing",
                    course="Academic Writing",
                    topic="Literature",
                    semester="Summer 2026",
                    source_type="md",
                )
                results = store.search([1.0, 0.0], top_k=2, filters={"course": "Local AI"})
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["doc_id"], "DOC-A")
                self.assertEqual(results[0]["page_number"], 2)
                filters = store.filter_values()
                self.assertIn("Local AI", filters["course"])
                self.assertIn("rag", filters["tags"])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
