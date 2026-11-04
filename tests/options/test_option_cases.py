"""Independent ADR-0002 parser controls, not option/algorithm execution tests."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import OptionValidationError, UnknownOptionError, UnsupportedOptionError
from pyelk.options import OPTION_SPECS, KNOWN_OPTION_IDS, Padding, resolve_options
from pyelk.options.generic import RUNTIME_PROPERTY_SPECS, parse_generic_mapping


P = "org.eclipse.elk."


class IndependentOptionCases(unittest.TestCase):
    def local(self, values):
        return resolve_options(local=values)

    def test_nine_defaults_separate_declaration_from_effective_fallback(self):
        result = resolve_options()
        expected = {P + "algorithm": P + "layered", P + "direction": "UNDEFINED",
                    P + "padding": Padding(top=12, right=12, bottom=12, left=12),
                    P + "spacing.nodeNode": 20, P + "layered.spacing.nodeNodeBetweenLayers": 20,
                    P + "spacing.componentComponent": 20, P + "separateConnectedComponents": True,
                    P + "edgeRouting": "ORTHOGONAL", P + "randomSeed": 1}
        self.assertEqual({key: result.values[key] for key in expected}, expected)
        self.assertEqual(len(OPTION_SPECS), 63)
        self.assertEqual(set(result.values), set(OPTION_SPECS))
        self.assertLess(set(expected), set(OPTION_SPECS))
        self.assertEqual(result.values[P + "portConstraints"], "UNDEFINED")
        self.assertEqual(result.values[P + "port.side"], "UNDEFINED")
        self.assertIsNone(result.values[P + "port.index"])
        self.assertEqual(result.values[P + "nodeSize.constraints"], frozenset())
        self.assertIs(result.values[P + "nodeSize.fixedGraphSize"], False)
        self.assertIsNone(OPTION_SPECS[P + "algorithm"].declared_default)
        self.assertEqual(OPTION_SPECS[P + "direction"].declared_default, "UNDEFINED")
        self.assertEqual(result.origins[P + "algorithm"], "layout-fallback")
        self.assertEqual(result.selected_global, "default")
        self.assertEqual(dict(result.raw_values), {})
        self.assertEqual(len(KNOWN_OPTION_IDS), 243)
        self.assertEqual(set(RUNTIME_PROPERTY_SPECS), set(KNOWN_OPTION_IDS))
        self.assertGreater(len(KNOWN_OPTION_IDS), len(OPTION_SPECS))

    def test_explicit_empty_call_replaces_constructor_and_then_local_wins(self):
        constructor = {"defaultLayoutOptions": {"elk.direction": "DOWN", "elk.spacing.nodeNode": 29}}
        args = {"layoutOptions": {}}
        local = {"elk.direction": "LEFT"}
        result = resolve_options(constructor=constructor, layout_arguments=args, local=local)
        self.assertEqual(result.selected_global, "call")
        self.assertEqual(result.values[P + "direction"], "LEFT")
        self.assertEqual(result.values[P + "spacing.nodeNode"], 20)
        self.assertEqual(result.origins[P + "direction"], "local")
        self.assertEqual(result.origins[P + "spacing.nodeNode"], "default")
        self.assertEqual(dict(result.raw_values), {P + "direction": "LEFT"})
        inherited = resolve_options(constructor=constructor, layout_arguments={})
        self.assertEqual(inherited.selected_global, "constructor")
        self.assertEqual(inherited.values[P + "spacing.nodeNode"], 29)

    def test_call_replacement_does_not_merge_unselected_values(self):
        result = resolve_options(constructor={"defaultLayoutOptions": {"elk.spacing.nodeNode": 99}},
                                 layout_arguments={"layoutOptions": {"elk.direction": "DOWN"}})
        self.assertEqual(result.values[P + "direction"], "DOWN")
        self.assertEqual(result.values[P + "spacing.nodeNode"], 20)
        self.assertNotIn(P + "spacing.nodeNode", result.raw_values)
        # The unselected mapping is a valid container whose contents are not parsed.
        replaced = resolve_options(constructor={"defaultLayoutOptions": {"vendor.notAnElkOption": object_value()}},
                                   layout_arguments={"layoutOptions": {}})
        self.assertEqual(replaced.selected_global, "call")

    def test_every_explicit_option_container_is_checked_even_when_not_selected(self):
        for bad in (None, False, 0, "", []):
            with self.subTest(bad=bad):
                with self.assertRaises(OptionValidationError) as caught:
                    resolve_options(constructor={"defaultLayoutOptions": bad}, layout_arguments={"layoutOptions": {}})
                self.assertEqual(caught.exception.path, "/constructor/defaultLayoutOptions")
                with self.assertRaises(OptionValidationError) as caught:
                    resolve_options(layout_arguments={"layoutOptions": bad})
                self.assertEqual(caught.exception.path, "/layoutArguments/layoutOptions")
        self.assertEqual(resolve_options(constructor=None, layout_arguments=None, local=None).selected_global, "default")
        for name in ("constructor", "layout_arguments", "local"):
            for bad in (False, 0, "", []):
                with self.subTest(name=name, bad=bad):
                    with self.assertRaises(OptionValidationError):
                        resolve_options(**{name: bad})

    def test_aliases_resolve_canonical_ids_and_same_scope_conflicts_reject(self):
        for key in (P + "direction", "elk.direction"):
            self.assertEqual(self.local({key: "DOWN"}).values[P + "direction"], "DOWN")
        for second in ("RIGHT", "LEFT"):
            with self.assertRaises(OptionValidationError) as caught:
                self.local({P + "direction": "RIGHT", "elk.direction": second})
            self.assertEqual(caught.exception.code, "AMBIGUOUS_OPTION")
        cross = resolve_options(layout_arguments={"layoutOptions": {P + "direction": "DOWN"}},
                                local={"elk.direction": "UP"})
        self.assertEqual(cross.values[P + "direction"], "UP")
        with self.assertRaises(UnknownOptionError):
            self.local({"direction": "RIGHT"})

    def test_known_unimplemented_is_distinct_from_unknown_and_never_silently_dropped(self):
        supported = self.local({P + "portConstraints": "FIXED_SIDE", "elk.port.side": "EAST"})
        self.assertEqual(supported.values[P + "portConstraints"], "FIXED_SIDE")
        self.assertEqual(supported.values[P + "port.side"], "EAST")
        # The compatibility resolver's boundary is not the generic registry's
        # boundary, nor a statement about executable algorithm availability.
        with self.assertRaises(UnsupportedOptionError) as known:
            self.local({P + "aspectRatio": 1.3})
        with self.assertRaises(UnknownOptionError) as unknown:
            self.local({"vendor.notAnElkOption": 1})
        self.assertNotEqual(type(known.exception), type(unknown.exception))
        self.assertNotEqual(known.exception.code, unknown.exception.code)
        self.assertEqual(known.exception.path, "/local/org.eclipse.elk.aspectRatio")
        self.assertEqual(unknown.exception.path, "/local/vendor.notAnElkOption")
        parsed, raw = parse_generic_mapping({P + "aspectRatio": 1.3})
        self.assertEqual(parsed, {P + "aspectRatio": 1.3})
        self.assertEqual(raw, {P + "aspectRatio": 1.3})

    def test_numeric_and_boolean_string_parsing_preserves_raw_types(self):
        values = {"elk.spacing.nodeNode": "0", "elk.layered.spacing.nodeNodeBetweenLayers": "3.5",
                  "elk.spacing.componentComponent": 1e-9, "elk.separateConnectedComponents": "FaLsE",
                  "elk.randomSeed": "0"}
        before = copy.deepcopy(values)
        result = self.local(values)
        self.assertEqual(result.values[P + "spacing.nodeNode"], 0)
        self.assertEqual(result.values[P + "layered.spacing.nodeNodeBetweenLayers"], 3.5)
        self.assertIs(result.values[P + "separateConnectedComponents"], False)
        self.assertIs(type(result.values[P + "randomSeed"]), int)
        self.assertEqual(result.values[P + "randomSeed"], 0)
        self.assertIs(type(result.raw_values[P + "spacing.nodeNode"]), str)
        self.assertEqual(values, before)

    def test_bool_is_not_a_number_and_nonfinite_spacing_never_passes(self):
        for bad in (True, False, None, -1, float("inf"), float("nan"), "NaN", "Infinity", "-0.01"):
            with self.subTest(bad=bad):
                with self.assertRaises(OptionValidationError) as caught:
                    self.local({"elk.spacing.nodeNode": bad})
                self.assertEqual(caught.exception.path, "/local/elk.spacing.nodeNode")
        for bad in (0, 1, "0", "yes", None):
            with self.subTest(boolean=bad):
                with self.assertRaises(OptionValidationError):
                    self.local({"elk.separateConnectedComponents": bad})

    def test_signed_int32_seed_domain_and_no_float_or_bool_coercion(self):
        for value in (-2147483648, 2147483647, 0, "-17"):
            self.assertEqual(self.local({"elk.randomSeed": value}).values[P + "randomSeed"], int(value))
        for bad in (-2147483649, 2147483648, True, False, 1.0, "1.0", None):
            with self.subTest(bad=bad):
                with self.assertRaises(OptionValidationError):
                    self.local({"elk.randomSeed": bad})

    def test_algorithm_names_and_enum_values_are_not_claimed_as_registered_execution(self):
        for value in ("layered", P + "layered"):
            result = self.local({"elk.algorithm": value})
            self.assertEqual(result.values[P + "algorithm"], P + "layered")
            self.assertEqual(result.origins[P + "algorithm"], "local")
        for field, value in (("elk.algorithm", "stress"), ("elk.direction", "right"),
                              ("elk.direction", 1), ("elk.edgeRouting", "POLYLINE")):
            with self.subTest(field=field, value=value):
                with self.assertRaises(OptionValidationError):
                    self.local({field: value})

    def test_padding_four_sides_parse_from_mapping_and_official_string(self):
        expected = Padding(top=3, right=3, bottom=2, left=2)
        mapping = {"left": 2, "top": 3, "right": 3, "bottom": 2}
        self.assertEqual(self.local({"elk.padding": mapping}).values[P + "padding"], expected)
        self.assertEqual(self.local({"elk.padding": "[left=2, top=3, right=3, bottom=2]"}).values[P + "padding"], expected)
        with self.assertRaises((AttributeError, TypeError)):
            expected.top = 500

    def test_padding_rejects_incomplete_duplicate_unknown_or_invalid_sides(self):
        for bad in ({"top": 1}, {"top": 1, "right": 2, "bottom": 3, "left": -1},
                    {"top": 1, "right": 2, "bottom": 3, "left": True},
                    {"top": 1, "right": 2, "bottom": 3, "left": 4, "extra": 5},
                    "[top=1,left=2,bottom=3]", "[top=1,top=2,left=3,right=4,bottom=5]", None):
            with self.subTest(bad=bad):
                with self.assertRaises(OptionValidationError):
                    self.local({"elk.padding": bad})

    def test_raw_values_and_parsed_results_are_cloned_and_readonly(self):
        padding = {"top": 1, "right": 2, "bottom": 3, "left": 4}
        local = {"elk.padding": padding}
        result = self.local(local)
        padding["top"] = 99
        self.assertEqual(result.values[P + "padding"].top, 1)
        first = result.raw_values
        first[P + "padding"]["left"] = 88
        self.assertEqual(result.raw_values[P + "padding"]["left"], 4)
        for mapping in (result.values, result.origins, result.raw_values):
            with self.assertRaises(TypeError):
                mapping[P + "padding"] = None
        self.assertEqual(result.values[P + "padding"].left, 4)

    def test_all_caller_containers_remain_exact_and_independently_owned(self):
        constructor = {"defaultLayoutOptions": {"elk.direction": "DOWN"}, "business": {"error": {"stack": "keep"}}}
        args = {"layoutOptions": {"elk.padding": {"top": 1, "right": 2, "bottom": 3, "left": 4}}, "logging": False}
        local = {"elk.randomSeed": 0}
        originals = copy.deepcopy((constructor, args, local))
        resolved = resolve_options(constructor=constructor, layout_arguments=args, local=local)
        self.assertEqual((constructor, args, local), originals)
        args["layoutOptions"]["elk.padding"]["left"] = 700
        self.assertEqual(resolved.raw_values[P + "padding"]["left"], 4)


def object_value():
    """Valid JSON data in an unselected mapping, never an arbitrary Python object."""
    return {"nested": [False, 0, None]}


if __name__ == "__main__":
    unittest.main()
