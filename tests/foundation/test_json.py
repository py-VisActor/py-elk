"""Host JSON ownership and validation, independent of layout algorithms."""
from pathlib import Path
import sys
from types import MappingProxyType
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import ModelValidationError, ValidationError
from pyelk._json import clone_json, finite_number, pointer


class JsonOwnershipTests(unittest.TestCase):
    def test_business_values_and_nested_copies_are_lossless_and_isolated(self):
        original = {"missingTest": {}, "zero": 0, "false": False, "null": None,
                    "$H": 0, "error": {"stack": "business"}, "ordered": ["b", "a"]}
        copied = clone_json(original)
        self.assertEqual(list(copied), list(original))
        self.assertIs(copied["false"], False)
        self.assertIsNone(copied["null"])
        self.assertEqual(copied, original)
        copied["error"]["stack"] = "changed"
        original["ordered"].append("c")
        self.assertEqual(original["error"]["stack"], "business")
        self.assertEqual(copied["ordered"], ["b", "a"])

    def test_mapping_is_copied_without_preserving_external_mutability(self):
        source = {"nested": {"n": 1}}
        copied = clone_json(MappingProxyType(source))
        source["nested"]["n"] = 2
        self.assertIs(type(copied), dict)
        self.assertEqual(copied, {"nested": {"n": 1}})

    def test_shared_children_are_copied_independently_without_becoming_cycles(self):
        child = {"list": []}
        copied = clone_json([child, child])
        copied[0]["list"].append(1)
        self.assertEqual(copied[1], {"list": []})
        self.assertEqual(child, {"list": []})

    def test_cycles_have_exact_escaped_json_pointer(self):
        data = {}
        data["a/b~"] = data
        with self.assertRaises(ValidationError) as caught:
            clone_json(data)
        self.assertEqual(caught.exception.code, "INVALID_JSON")
        self.assertEqual(caught.exception.path, "/a~1b~0")

    def test_non_json_values_keys_and_nonfinite_business_numbers_are_rejected(self):
        for value in [float("nan"), float("inf"), float("-inf"), (1, 2), object(), {0: "integer key"}]:
            with self.subTest(value=type(value).__name__), self.assertRaises(ValidationError):
                clone_json({"business": value})

    def test_nested_failure_uses_callers_error_class_and_path(self):
        with self.assertRaises(ModelValidationError) as caught:
            clone_json({"items": [object()]}, path="/graph", error_type=ModelValidationError)
        self.assertEqual(caught.exception.path, "/graph/items/0")

    def test_integral_ids_can_remain_integers_without_float_coercion(self):
        large = 10 ** 400
        self.assertEqual(clone_json({"id": large}), {"id": large})
        self.assertIs(type(clone_json(1.0)), float)
        self.assertIs(type(clone_json(1)), int)

    def test_geometry_rejects_bool_nonfinite_negative_and_overflow(self):
        for value in [True, "1", None, float("nan"), float("inf"), -1, 10 ** 400]:
            with self.subTest(value=type(value).__name__), self.assertRaises(ValidationError) as caught:
                finite_number(value, path="/width", nonnegative=True)
            self.assertEqual(caught.exception.path, "/width")
        self.assertEqual(finite_number(0, path="/width", nonnegative=True), 0)
        self.assertEqual(finite_number(-2.5, path="/x"), -2.5)

    def test_pointer_encodes_one_component_without_rewriting_parent(self):
        self.assertEqual(pointer("/children/0", "a~/b"), "/children/0/a~0~1b")
        self.assertEqual(pointer("", 0), "/0")


if __name__ == "__main__":
    unittest.main()
