"""Internal option parsing tests; no layout algorithm is exercised."""
import copy
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
from types import MappingProxyType
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import OptionValidationError, UnknownOptionError, UnsupportedOptionError
from pyelk.options import KNOWN_OPTION_IDS, OPTION_SPECS, Padding, resolve_options
from pyelk.options.generic import RUNTIME_PROPERTY_SPECS, parse_generic_mapping

PREFIX = "org.eclipse.elk."


class OptionResolutionTests(unittest.TestCase):
    def test_declared_and_effective_defaults_are_distinct(self):
        resolved = resolve_options()
        # The compatibility resolver retains its original nine defaults and
        # now also declares the source-bound node/port/provider schemas.
        self.assertEqual(len(OPTION_SPECS), 63)
        self.assertEqual(len(KNOWN_OPTION_IDS), 243)
        self.assertEqual(set(RUNTIME_PROPERTY_SPECS), set(KNOWN_OPTION_IDS))
        self.assertEqual(set(resolved.values), set(OPTION_SPECS))
        self.assertIsNone(OPTION_SPECS[PREFIX + "algorithm"].declared_default)
        self.assertEqual(resolved.values[PREFIX + "algorithm"], PREFIX + "layered")
        self.assertEqual(resolved.origins[PREFIX + "algorithm"], "layout-fallback")
        self.assertEqual(resolved.values[PREFIX + "direction"], "UNDEFINED")
        self.assertEqual(resolved.values[PREFIX + "padding"], Padding(top=12, right=12, bottom=12, left=12))
        for suffix in ("spacing.nodeNode", "layered.spacing.nodeNodeBetweenLayers", "spacing.componentComponent"):
            self.assertEqual(resolved.values[PREFIX + suffix], 20)
        self.assertIs(resolved.values[PREFIX + "separateConnectedComponents"], True)
        self.assertEqual(resolved.values[PREFIX + "edgeRouting"], "ORTHOGONAL")
        self.assertEqual(resolved.values[PREFIX + "randomSeed"], 1)
        self.assertEqual(resolved.values[PREFIX + "port.side"], "UNDEFINED")
        self.assertEqual(resolved.values[PREFIX + "portConstraints"], "UNDEFINED")
        self.assertIsNone(resolved.values[PREFIX + "port.anchor"])
        self.assertIsNone(resolved.values[PREFIX + "port.index"])
        self.assertEqual(resolved.selected_global, "default")

    def test_full_ids_and_elk_aliases_parse_the_same_nine_values(self):
        values = ["layered", "UP", {"top": 1, "right": 2, "bottom": 3, "left": 4}, "2.5", 33, "FaLsE", "4e1", "ORTHOGONAL", "0"]
        full = {spec.id: value for spec, value in zip(OPTION_SPECS.values(), values)}
        short = {spec.alias: value for spec, value in zip(OPTION_SPECS.values(), values)}
        self.assertEqual(resolve_options(local=full).values, resolve_options(local=short).values)
        self.assertIs(resolve_options(local=short).values[PREFIX + "separateConnectedComponents"], False)
        self.assertEqual(resolve_options(local=short).values[PREFIX + "randomSeed"], 0)

    def test_explicit_call_empty_mapping_replaces_constructor(self):
        constructor = {"defaultLayoutOptions": {"elk.direction": "DOWN", "elk.randomSeed": 7}}
        inherited = resolve_options(constructor=constructor)
        empty_call = resolve_options(constructor=constructor, layout_arguments={"layoutOptions": {}})
        self.assertEqual(inherited.values[PREFIX + "direction"], "DOWN")
        self.assertEqual(inherited.origins[PREFIX + "direction"], "constructor")
        self.assertEqual(empty_call.values[PREFIX + "direction"], "UNDEFINED")
        self.assertEqual(empty_call.values[PREFIX + "randomSeed"], 1)
        self.assertEqual(empty_call.selected_global, "call")

    def test_select_global_before_local_override_without_constructor_leak(self):
        result = resolve_options(constructor={"defaultLayoutOptions": {"elk.direction": "DOWN", "elk.randomSeed": 7}},
                                 layout_arguments={"layoutOptions": {"elk.spacing.nodeNode": 31}},
                                 local={"org.eclipse.elk.direction": "LEFT"})
        self.assertEqual(result.values[PREFIX + "direction"], "LEFT")
        self.assertEqual(result.origins[PREFIX + "direction"], "local")
        self.assertEqual(result.values[PREFIX + "spacing.nodeNode"], 31)
        self.assertEqual(result.origins[PREFIX + "spacing.nodeNode"], "call")
        self.assertEqual(result.values[PREFIX + "randomSeed"], 1)

    def test_unselected_constructor_keys_and_values_are_not_parsed(self):
        result = resolve_options(constructor={"defaultLayoutOptions": {"vendor.unknown": 1, "elk.direction": False}},
                                 layout_arguments={"layoutOptions": {}})
        self.assertEqual(result.values[PREFIX + "direction"], "UNDEFINED")
        self.assertEqual(result.raw_values, {})

    def test_explicit_containers_are_mappings_even_when_replaced(self):
        for value in (None, False, 0, "", []):
            for owner in ("constructor", "call", "local"):
                with self.subTest(owner=owner, value=value):
                    kwargs = ({"constructor": {"defaultLayoutOptions": value}, "layout_arguments": {"layoutOptions": {}}}
                              if owner == "constructor" else {"layout_arguments": {"layoutOptions": value}}
                              if owner == "call" else {"local": value})
                    if owner == "local" and value is None:
                        self.assertEqual(resolve_options(**kwargs).selected_global, "default")
                    else:
                        with self.assertRaises(OptionValidationError) as caught:
                            resolve_options(**kwargs)
                        self.assertEqual(caught.exception.code, "INVALID_OPTION_CONTAINER")

    def test_outer_none_is_omission_but_other_falsy_outer_values_reject(self):
        self.assertEqual(resolve_options(constructor=None, layout_arguments=None, local=None).values, resolve_options().values)
        for value in (False, 0, "", []):
            for name in ("constructor", "layout_arguments", "local"):
                with self.subTest(name=name, value=value), self.assertRaises(OptionValidationError):
                    resolve_options(**{name: value})

    def test_same_scope_aliases_conflict_even_with_equal_values(self):
        for scope in ("local", "constructor", "call"):
            options = {"elk.direction": "LEFT", PREFIX + "direction": "LEFT"}
            kwargs = {"local": options} if scope == "local" else {"constructor": {"defaultLayoutOptions": options}} if scope == "constructor" else {"layout_arguments": {"layoutOptions": options}}
            with self.subTest(scope=scope), self.assertRaises(OptionValidationError) as caught:
                resolve_options(**kwargs)
            self.assertEqual(caught.exception.code, "AMBIGUOUS_OPTION")

    def test_cross_scope_alias_override_is_legal(self):
        result = resolve_options(constructor={"defaultLayoutOptions": {PREFIX + "direction": "DOWN"}}, local={"elk.direction": "UP"})
        self.assertEqual(result.values[PREFIX + "direction"], "UP")

    def test_unknown_and_known_unimplemented_are_different_errors(self):
        for key in ("vendor.option", "direction", "notAnElkOption"):
            with self.subTest(key=key):
                with self.assertRaises(UnknownOptionError) as caught:
                    resolve_options(local={key: 1})
                self.assertEqual(caught.exception.code, "UNKNOWN_OPTION")
                self.assertEqual(caught.exception.path, "/local/" + key)
        self.assertEqual(resolve_options(local={"nodeNode": 7}).values[PREFIX + "spacing.nodeNode"], 7)
        self.assertEqual(resolve_options(local={"elk.port.side": "NORTH"}).values[PREFIX + "port.side"], "NORTH")
        for key in (PREFIX + "aspectRatio", "elk.aspectRatio"):
            with self.subTest(key=key):
                # This compatibility entrypoint is narrower than the full
                # native property registry; known is distinct from unknown.
                with self.assertRaises(UnsupportedOptionError) as caught:
                    resolve_options(local={key: 1})
                self.assertEqual(caught.exception.code, "UNSUPPORTED_OPTION")
                parsed, raw = parse_generic_mapping({key: 1.3})
                self.assertEqual(parsed, {PREFIX + "aspectRatio": 1.3})
                self.assertEqual(raw, {PREFIX + "aspectRatio": 1.3})

    def test_numeric_spacing_is_finite_nonnegative_and_not_bool(self):
        for value, expected in [(0, 0), (0.0, 0.0), ("0", 0), (".25", 0.25), ("+1.2e2", 120)]:
            self.assertEqual(resolve_options(local={"elk.spacing.nodeNode": value}).values[PREFIX + "spacing.nodeNode"], expected)
        for bad in (True, False, None, -1, "-1", "NaN", "Infinity", "1e999", " 3 ", [], {}):
            with self.subTest(bad=bad), self.assertRaises(OptionValidationError):
                resolve_options(local={"elk.spacing.nodeNode": bad})

    def test_seed_retains_signed_32_bit_integer_without_rng_claim(self):
        for value in (-(2**31), 0, 2**31 - 1, "-2147483648", "+0", "2147483647"):
            self.assertEqual(resolve_options(local={"elk.randomSeed": value}).values[PREFIX + "randomSeed"], int(value))
        for bad in (True, False, 1.0, "1.0", "1e1", 2**31, -(2**31) - 1, None):
            with self.subTest(bad=bad), self.assertRaises(OptionValidationError):
                resolve_options(local={"elk.randomSeed": bad})

    def test_boolean_strings_are_not_python_truthiness(self):
        for value, expected in [(True, True), (False, False), ("TRUE", True), ("false", False)]:
            self.assertIs(resolve_options(local={"elk.separateConnectedComponents": value}).values[PREFIX + "separateConnectedComponents"], expected)
        for bad in (0, 1, "0", "1", " false ", None):
            with self.subTest(bad=bad), self.assertRaises(OptionValidationError):
                resolve_options(local={"elk.separateConnectedComponents": bad})

    def test_padding_has_four_explicit_sides_and_never_infers_missing_sides(self):
        expected = Padding(top=11, right=31, bottom=23, left=17)
        self.assertEqual(resolve_options(local={"elk.padding": "[top=11,left=17,bottom=23,right=31]"}).values[PREFIX + "padding"], expected)
        self.assertEqual(resolve_options(local={"elk.padding": {"top": 11, "right": 31, "bottom": 23, "left": 17}}).values[PREFIX + "padding"], expected)
        for bad in (12, None, "[top=1]", "[top=1,left=1,bottom=1,right=1,top=2]", "[top=1;left=1;bottom=1;right=1]", {"top": 1}, {"top": -1, "right": 1, "bottom": 1, "left": 1}, {"top": True, "right": 1, "bottom": 1, "left": 1}):
            with self.subTest(bad=bad), self.assertRaises(OptionValidationError):
                resolve_options(local={"elk.padding": bad})

    def test_enum_names_only_and_no_unimplemented_algorithm_or_routing(self):
        for name in ("UNDEFINED", "RIGHT", "LEFT", "DOWN", "UP"):
            self.assertEqual(resolve_options(local={"elk.direction": name}).values[PREFIX + "direction"], name)
        for bad in ("right", "1", 1, None):
            with self.subTest(bad=bad), self.assertRaises(OptionValidationError):
                resolve_options(local={"elk.direction": bad})
        for key, value in [("elk.algorithm", "stress"), ("elk.edgeRouting", "SPLINES"), ("elk.edgeRouting", "UNDEFINED")]:
            with self.subTest(key=key, value=value), self.assertRaises(OptionValidationError):
                resolve_options(local={key: value})

    def test_inputs_raw_values_and_typed_results_have_independent_ownership(self):
        local = MappingProxyType({"elk.padding": {"top": 1, "right": 2, "bottom": 3, "left": 4}})
        original = copy.deepcopy(dict(local))
        result = resolve_options(local=local)
        self.assertEqual(local, original)
        raw = result.raw_values
        raw[PREFIX + "padding"]["top"] = 999
        self.assertEqual(result.raw_values[PREFIX + "padding"]["top"], 1)
        self.assertEqual(result.values[PREFIX + "padding"].top, 1)
        with self.assertRaises(TypeError):
            result.values[PREFIX + "direction"] = "RIGHT"
        with self.assertRaises(TypeError):
            result.origins[PREFIX + "direction"] = "local"
        with self.assertRaises(FrozenInstanceError):
            result.values[PREFIX + "padding"].top = 2

    def test_json_and_error_paths_preserve_business_types_and_escape_keys(self):
        with self.assertRaises(UnknownOptionError) as caught:
            resolve_options(local={"vendor/a~b": False})
        self.assertEqual(caught.exception.path, "/local/vendor~1a~0b")
        for value in ({1: 2}, {"elk.padding": float("inf")}):
            with self.subTest(value=value), self.assertRaises(OptionValidationError):
                resolve_options(local=value)


if __name__ == "__main__":
    unittest.main()
