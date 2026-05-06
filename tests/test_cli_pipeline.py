from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles.cli import main
from ruwritingstyles.segment import normalize_document, segment_markdown


class SegmentTests(unittest.TestCase):
    def test_segment_markdown_headings_paragraphs_and_code(self) -> None:
        text = normalize_document(
            """# Title

First paragraph.

```text
code
```

## Next
Second paragraph.
"""
        )

        segments = segment_markdown(text)
        self.assertEqual([segment.segment_type for segment in segments], ["heading", "paragraph", "code", "heading", "paragraph"])
        self.assertEqual([segment.span_id for segment in segments], ["h001", "p002", "c003", "h004", "p005"])


class CliPipelineTests(unittest.TestCase):
    run_dir = ROOT / "runs" / "unittest-readme"

    def tearDown(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_full_offline_run_creates_expected_artifacts(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

        exit_code = main(["run", "README.md", "--run-id", "unittest-readme"])
        self.assertEqual(exit_code, 0)

        self.assertTrue((self.run_dir / "segments.json").exists())
        self.assertTrue((self.run_dir / "council.json").exists())
        self.assertTrue((self.run_dir / "revision.json").exists())
        self.assertTrue((self.run_dir / "verification.json").exists())

        reviews = sorted((self.run_dir / "reviews").glob("*.review.json"))
        prompts = sorted((self.run_dir / "reviews").glob("*.prompt.md"))
        self.assertEqual(len(reviews), 3)
        self.assertEqual(len(prompts), 3)

        segments = json.loads((self.run_dir / "segments.json").read_text(encoding="utf-8"))
        self.assertEqual(segments["segment_count"], len(segments["segments"]))
        self.assertEqual(segments["segments"][0]["span_id"], "h001")

        verification = json.loads((self.run_dir / "verification.json").read_text(encoding="utf-8"))
        self.assertEqual(verification["status"], "prompt_ready")

        self.assertEqual(main(["validate-run", str(self.run_dir)]), 0)


if __name__ == "__main__":
    unittest.main()
