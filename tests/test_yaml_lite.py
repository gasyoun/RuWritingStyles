import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.config import load_passport_dicts

from ruwritingstyles.yaml_lite import (
    block,
    list_items,
    parse_scalar,
    parse_simple_yaml,
    scalar,
)


class ParseScalarTests(unittest.TestCase):
    def test_coercions(self) -> None:
        self.assertEqual(parse_scalar("true"), True)
        self.assertEqual(parse_scalar("false"), False)
        self.assertIsNone(parse_scalar("null"))
        self.assertIsNone(parse_scalar("~"))
        self.assertEqual(parse_scalar("42"), 42)
        self.assertEqual(parse_scalar("1.5"), 1.5)
        self.assertEqual(parse_scalar('"quoted"'), "quoted")
        self.assertEqual(parse_scalar("plain text"), "plain text")


class ParseSimpleYamlTests(unittest.TestCase):
    def test_nested_dict_and_list(self) -> None:
        data = parse_simple_yaml("a:\n  b: 1\n  c:\n    - x\n    - y\n")
        self.assertEqual(data, {"a": {"b": 1, "c": ["x", "y"]}})

    def test_list_of_dicts(self) -> None:
        data = parse_simple_yaml("items:\n  - id: one\n    n: 1\n  - id: two\n    n: 2\n")
        self.assertEqual(data, {"items": [{"id": "one", "n": 1}, {"id": "two", "n": 2}]})

    def test_colon_inside_quoted_value_is_not_a_separator(self) -> None:
        # Regression: a passport name whose value contains ": " previously broke
        # the CI parser (it split on the inner colon).
        data = parse_simple_yaml('name: "«Слово» — взгляд: лингвиста"\n')
        self.assertEqual(data, {"name": "«Слово» — взгляд: лингвиста"})

    def test_colon_inside_quoted_list_item(self) -> None:
        data = parse_simple_yaml('sources:\n  - "Зализняк: очерк"\n  - "Tubb 2007"\n')
        self.assertEqual(data, {"sources": ["Зализняк: очерк", "Tubb 2007"]})


class TargetedHelpersTests(unittest.TestCase):
    def test_scalar_tolerates_colon_in_quotes(self) -> None:
        self.assertEqual(scalar('name: "a: b"\n', "name"), "a: b")

    def test_scalar_default(self) -> None:
        self.assertEqual(scalar("x: 1\n", "missing", "fallback"), "fallback")

    def test_block_and_list_items(self) -> None:
        text = "mvp:\n  - one\n  - two\nother: z\n"
        self.assertEqual(list_items(block(text, "mvp")), ("one", "two"))

    def test_list_items_tolerate_colon_in_quotes(self) -> None:
        self.assertEqual(list_items('  - "a: b"\n  - c\n'), ("a: b", "c"))


class GenericAndTargetedAgreeTests(unittest.TestCase):
    def test_same_value_for_quoted_colon_field(self) -> None:
        text = 'name: "Зависимость: разбор"\n'
        generic = parse_simple_yaml(text)["name"]
        targeted = scalar(text, "name")
        self.assertEqual(generic, targeted)
        self.assertEqual(generic, "Зависимость: разбор")


class PassportLoaderTests(unittest.TestCase):
    def test_existing_malformed_passport_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            passports = root / "styles" / "passports"
            passports.mkdir(parents=True)
            (passports / "broken.yml").write_text("- not\n- an\n- object\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed style passport"):
                load_passport_dicts(root)


if __name__ == "__main__":
    unittest.main()
