import unittest

from ruwritingstyles.schema_validation import lint_schema, validate_json_schema


class LintSchemaTests(unittest.TestCase):
    def test_supported_subset_passes(self) -> None:
        schema = {
            "type": "object",
            "required": ["a"],
            "properties": {
                "a": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "b": {"type": "string", "format": "date-time"},
            },
            "additionalProperties": False,
        }
        self.assertEqual(lint_schema(schema), ())

    def test_unsupported_keyword_is_flagged(self) -> None:
        msgs = lint_schema({"type": "object", "oneOf": [], "properties": {"x": {"uniqueItems": True}}})
        joined = " ".join(msgs)
        self.assertIn("oneOf", joined)
        self.assertIn("uniqueItems", joined)


class EnforcedKeywordTests(unittest.TestCase):
    def test_min_items_enforced(self) -> None:
        schema = {"type": "array", "items": {"type": "string"}, "minItems": 1}
        self.assertTrue(validate_json_schema([], schema))      # too short -> error
        self.assertEqual(validate_json_schema(["x"], schema), ())

    def test_min_properties_enforced(self) -> None:
        schema = {"type": "object", "minProperties": 1}
        self.assertTrue(validate_json_schema({}, schema))
        self.assertEqual(validate_json_schema({"k": 1}, schema), ())

    def test_date_time_format_enforced(self) -> None:
        schema = {"type": "string", "format": "date-time"}
        self.assertTrue(validate_json_schema("not-a-date", schema))
        self.assertEqual(validate_json_schema("2026-06-13T10:00:00+03:00", schema), ())
        self.assertEqual(validate_json_schema("2026-06-13 10:00:00", schema), ())

    def test_max_length_enforced(self) -> None:
        schema = {"type": "string", "maxLength": 3}
        self.assertTrue(validate_json_schema("abcd", schema))
        self.assertEqual(validate_json_schema("abc", schema), ())


if __name__ == "__main__":
    unittest.main()
