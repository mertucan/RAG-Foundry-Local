import tempfile
import unittest
from pathlib import Path

from app.evaluate import evaluate_question, summarize
from app.vector_store import VectorStore


class StaticEmbedder:
    def embed(self, text):
        return [1.0, 0.0] if "gas leak" in text.lower() else [0.0, 1.0]


class EvaluationTests(unittest.TestCase):
    def test_evaluate_question_marks_expected_doc_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = VectorStore(Path(tmp) / "rag.db")
            try:
                store.insert("DOC-IP-001", "Gas Leak", "Inspection", 0, "gas leak detection", [1.0, 0.0])
                store.insert("DOC-OTHER", "Other", "General", 0, "general safety", [0.0, 1.0])
                result = evaluate_question(
                    store,
                    StaticEmbedder(),
                    {
                        "id": "EVAL-001",
                        "question": "How do I detect a gas leak?",
                        "expected_doc_ids": ["DOC-IP-001"],
                    },
                    top_k=1,
                )
                self.assertTrue(result["hit"])
                self.assertEqual(result["retrieved_doc_ids"], ["DOC-IP-001"])
            finally:
                store.close()

    def test_summarize_reports_hit_rate(self):
        summary = summarize([{"hit": True}, {"hit": False}, {"hit": True}])
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["hits"], 2)
        self.assertEqual(summary["hit_rate"], 0.667)


if __name__ == "__main__":
    unittest.main()
