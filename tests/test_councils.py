import argparse
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from ruwritingstyles.cli import _selected_style_ids
from ruwritingstyles.config import load_manifest


class CouncilResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(REPO_ROOT)

    def test_manifest_defines_named_councils(self) -> None:
        names = self.manifest.council_names()
        self.assertIn("general", names)
        self.assertIn("sanskrit", names)

    def test_general_council_equals_mvp(self) -> None:
        # `general` is the historical default; keep them in lockstep.
        self.assertEqual(
            self.manifest.resolve_council("general"),
            tuple(self.manifest.mvp_style_ids),
        )

    def test_sanskrit_council_is_sanskrit_weighted(self) -> None:
        ids = self.manifest.resolve_council("sanskrit")
        self.assertIn("elizarenkova-veda", ids)
        self.assertIn("panini-traditional", ids)
        # And it must NOT be the general panel.
        self.assertNotEqual(ids, tuple(self.manifest.mvp_style_ids))

    def test_unknown_council_resolves_empty(self) -> None:
        self.assertEqual(self.manifest.resolve_council("does-not-exist"), ())

    def test_council_style_ids_are_real_passports(self) -> None:
        passport_ids = {p.style_id for p in self.manifest.passports}
        for name, style_ids in self.manifest.councils:
            for style_id in style_ids:
                self.assertIn(style_id, passport_ids, f"council {name}: {style_id}")


class SelectedStyleIdsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(REPO_ROOT)

    def _args(self, **kw) -> argparse.Namespace:
        base = {"council": None, "mvp": False, "styles": None, "style": None}
        base.update(kw)
        return argparse.Namespace(**base)

    def test_council_flag_selects_council_styles(self) -> None:
        ids = _selected_style_ids(self._args(council="sanskrit"), self.manifest)
        self.assertEqual(ids, list(self.manifest.resolve_council("sanskrit")))

    def test_unknown_council_flag_raises_with_available_list(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _selected_style_ids(self._args(council="bogus"), self.manifest)
        self.assertIn("sanskrit", str(ctx.exception))

    def test_default_is_still_mvp(self) -> None:
        ids = _selected_style_ids(self._args(), self.manifest)
        self.assertEqual(ids, list(self.manifest.mvp_style_ids))


class CouncilIntegrityCheckTests(unittest.TestCase):
    def test_validate_catches_unknown_council_style_id(self) -> None:
        from validate_project import check_cross_references

        manifest_data = {
            "passports": [],
            "councils": {"broken": ["no-such-style"]},
        }
        errors = check_cross_references(manifest_data)
        self.assertTrue(
            any("no-such-style" in e and "broken" in e for e in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main()
