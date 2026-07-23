import unittest

from app.document_loader import LoadedDocument, is_supported_document, load_text_document


class DocumentLoaderTests(unittest.TestCase):
    def test_supported_extensions_include_pdf(self):
        self.assertTrue(is_supported_document("notes.md"))
        self.assertTrue(is_supported_document("notes.txt"))
        self.assertTrue(is_supported_document("paper.pdf"))
        self.assertFalse(is_supported_document("archive.zip"))

    def test_text_document_uses_front_matter(self):
        doc = load_text_document(
            "---\ntitle: Course Notes\ncategory: Study\nid: DOC-COURSE\ncourse: Local AI\ntags: rag, notes\n---\n\n# Notes\n\nRAG summary.",
            "notes.md",
        )
        self.assertEqual(doc.doc_id, "DOC-COURSE")
        self.assertEqual(doc.title, "Course Notes")
        self.assertEqual(doc.category, "Study")
        self.assertEqual(doc.course, "Local AI")
        self.assertEqual(doc.tags, "rag, notes")
        self.assertIn("RAG summary", doc.body)

    def test_loaded_document_shape_for_pdf_mocks(self):
        doc = LoadedDocument("paper", "Paper", "PDF Notes", "Extracted academic text.")
        self.assertEqual(doc.category, "PDF Notes")


if __name__ == "__main__":
    unittest.main()
