"""Schema tests for claim-faithfulness audit packets."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from ruwritingstyles.schema_validation import lint_schema, validate_json_schema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "claim-faithfulness-audit.schema.json").read_text(encoding="utf-8"))


def valid_packet() -> dict:
    return {
        "run_id": "claim-audit-smoke",
        "status": "draft",
        "source_protocol": "docs/claim-faithfulness-audit.md",
        "reviewers": ["A", "B"],
        "claims": [
            {
                "claim_id": "claim-001",
                "span_id": "p001",
                "claim_text": "The cited grammar supports this etymology.",
                "citation_ids": ["Whitney 1889"],
                "locator": {"kind": "page", "target": "p. 42"},
                "support_status": "needs_human_review",
                "severity": "warn",
                "rationale": "Locator is present but the source has not been checked.",
                "reviewer_action": "Open the cited page and confirm support.",
            }
        ],
        "calibration": {
            "precision": 1.0,
            "recall": 0.8,
            "false_positive_rate": 0.0,
            "false_negative_rate": 0.2,
            "agreement": 0.9,
            "notes": "Fixture values for schema validation only.",
        },
    }


class ClaimFaithfulnessSchemaTests(unittest.TestCase):
    def test_schema_uses_supported_keywords(self) -> None:
        self.assertEqual(lint_schema(SCHEMA), ())

    def test_valid_packet_passes(self) -> None:
        self.assertEqual(validate_json_schema(valid_packet(), SCHEMA), ())

    def test_claim_requires_support_status(self) -> None:
        packet = valid_packet()
        del packet["claims"][0]["support_status"]
        errors = validate_json_schema(packet, SCHEMA)
        self.assertIn("$.claims[0]: missing required property support_status", errors)

    def test_invalid_status_is_rejected(self) -> None:
        packet = valid_packet()
        packet["claims"][0]["support_status"] = "citation_exists"
        errors = validate_json_schema(packet, SCHEMA)
        self.assertTrue(any("support_status" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
