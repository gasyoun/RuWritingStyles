import unittest
from pathlib import Path
import tempfile
import shutil
from ruwritingstyles.citations import extract_citations, verify_citations_against_knowledge

class TestCitations(unittest.TestCase):
    def test_extract_citations(self):
        text = "Как отмечал (Зализняк 2004), ударение важно. Также см. [Тронский 1960] и @Gasparov1984."
        cites = extract_citations(text)
        self.assertIn("Зализняк 2004", cites)
        self.assertIn("Тронский 1960", cites)
        self.assertIn("Gasparov1984", cites)

    def test_email_address_is_not_extracted_as_citation(self):
        # Real false positive found on a live article: the author's contact
        # "gasyoun@gmail.com" must not yield a "gmail" citation.
        text = "Автор: М. Ю. Гасунс (gasyoun@gmail.com). См. также @Smith2020."
        cites = extract_citations(text)
        self.assertNotIn("gmail", cites)
        self.assertIn("Smith2020", cites)


    def test_verify_citations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            k_dir = root / "knowledge" / "collections"
            k_dir.mkdir(parents=True)
            
            (k_dir / "zaliznyak.md").write_text("## Зализняк 2004\nТекст.", encoding="utf-8")
            
            cites = ["Зализняк 2004", "Unknown 2026"]
            results = verify_citations_against_knowledge(root, cites)
            
            self.assertEqual(len(results["verified"]), 1)
            self.assertEqual(results["verified"][0]["citation"], "Зализняк 2004")
            self.assertEqual(len(results["not_in_bibliography"]), 1)
            self.assertEqual(results["not_in_bibliography"][0]["citation"], "Unknown 2026")

if __name__ == "__main__":
    unittest.main()
