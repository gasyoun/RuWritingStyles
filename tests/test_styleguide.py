from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from ruwritingstyles.styleguide import generate_stylebook_markdown


REPO_ROOT = Path(__file__).resolve().parents[1]


class StyleguideTests(unittest.TestCase):
    def test_generation_uses_in_repo_parser_without_pyyaml(self) -> None:
        original_import = __import__

        def reject_pyyaml(name, *args, **kwargs):
            if name == "yaml":
                raise AssertionError("styleguide must not import PyYAML")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=reject_pyyaml):
            markdown = generate_stylebook_markdown(REPO_ROOT)

        self.assertIn("## 1. Style Agents (Passports)", markdown)
        self.assertIn("**Constraints (Limits):**", markdown)


if __name__ == "__main__":
    unittest.main()
