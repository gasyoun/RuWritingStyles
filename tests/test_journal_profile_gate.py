"""Tests for the D10 verified gate on journal profiles (S1.3)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles.journals import proposed_profile_diff  # noqa: E402
from ruwritingstyles.project import UnverifiedJournalProfile, set_journal_profile  # noqa: E402


class TestVerifiedGateTests:
    def test_unverified_profile_is_refused(self):
        profile = {"id": "x", "name": "X", "verified": False, "guidelines_url": "https://example.com/g"}
        with tempfile.TemporaryDirectory() as tmp:
            try:
                set_journal_profile(Path(tmp), profile)
            except UnverifiedJournalProfile as exc:
                assert "example.com/g" in str(exc)
            else:
                raise AssertionError("expected UnverifiedJournalProfile")

    def test_missing_verified_flag_is_refused_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                set_journal_profile(Path(tmp), {"id": "x", "name": "X"})
            except UnverifiedJournalProfile:
                pass
            else:
                raise AssertionError("absent verified must read as false")

    def test_allow_unverified_escape(self):
        profile = {"id": "x", "name": "X", "verified": False}
        with tempfile.TemporaryDirectory() as tmp:
            path = set_journal_profile(Path(tmp), profile, allow_unverified=True)
            context = json.loads(path.read_text(encoding="utf-8"))
            assert context["journal_profile"]["id"] == "x"

    def test_verified_profile_attaches(self):
        profile = {"id": "x", "name": "X", "verified": True}
        with tempfile.TemporaryDirectory() as tmp:
            path = set_journal_profile(Path(tmp), profile)
            context = json.loads(path.read_text(encoding="utf-8"))
        assert context["journal_profile"]["verified"] is True


class TestProposedDiffTests:
    def test_diff_lists_changed_keys(self):
        lines = proposed_profile_diff({"id": "a", "max_chars": 30}, {"id": "a", "max_chars": 40})
        joined = "\n".join(lines)
        assert "max_chars" in joined and "30" in joined and "40" in joined
