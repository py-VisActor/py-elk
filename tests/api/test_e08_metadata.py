"""Exact full upstream registration, ownership and native metadata checks."""
import asyncio
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk import ELK
from pyelk._errors import (OptionValidationError, ResourceClosedError,
                           UnknownAlgorithmError, UnsupportedAlgorithmError,
                           UnsupportedWorkerError, UnsupportedFeatureError,
                           ValidationError)


def expected(mode="default"):
    return json.loads((ROOT / "tests/fixtures/suites/full-native-core/metadata-expected.json").read_bytes())["expectedQueries"][mode]


async def queries(instance):
    return {"algorithms": await instance.knownLayoutAlgorithms(),
            "options": await instance.knownLayoutOptions(),
            "categories": await instance.knownLayoutCategories()}


class NativeMetadataTests(unittest.TestCase):
    def instance(self, options=None, **kwargs):
        instance = ELK(options, **kwargs)
        self.addCleanup(instance.terminateWorker)
        return instance

    def test_default_queries_exact_frozen_native_shapes_and_reference_order(self):
        actual = asyncio.run(queries(self.instance()))
        self.assertEqual(actual, expected())
        self.assertEqual([len(actual[key]) for key in ("algorithms", "options", "categories")], [12, 243, 8])
        self.assertEqual({row["id"] for row in actual["algorithms"]},
                         {row["id"] for row in expected()["algorithms"]})

    def test_empty_algorithm_selection_retains_core_and_does_not_pollute_other_instances(self):
        empty = self.instance({"algorithms": []})
        full = self.instance()
        self.assertEqual(asyncio.run(queries(empty)), expected("algorithmsEmpty"))
        self.assertEqual(asyncio.run(queries(full)), expected())
        self.assertEqual([len(expected("algorithmsEmpty")[key]) for key in ("algorithms", "options", "categories")], [3, 94, 8])
        with self.assertRaises(UnknownAlgorithmError) as caught:
            asyncio.run(empty.layout({"id": "g", "layoutOptions": {"elk.algorithm": "layered"}, "children": [{"id": "c"}]}))
        self.assertEqual((caught.exception.code, caught.exception.path), ("UNKNOWN_ALGORITHM", ""))
        result = asyncio.run(empty.layout({"id": "g", "layoutOptions": {"elk.algorithm": "box"}, "children": [{"id": "c", "width": 10, "height": 5}]}))
        self.assertEqual(result["children"][0]["width"], 10)
        self.assertEqual(asyncio.run(queries(empty)), expected("algorithmsEmpty"))

    def test_aliases_and_duplicate_registration_are_normalized_without_changing_input(self):
        options = {"algorithms": ["layered", "org.eclipse.elk.layered", "layered"]}
        instance = self.instance(options)
        self.assertEqual(options["algorithms"], ["layered", "org.eclipse.elk.layered", "layered"])
        self.assertEqual(asyncio.run(queries(instance)), expected("layered"))
        options["algorithms"].clear()
        self.assertEqual(asyncio.run(queries(instance)), expected("layered"))

    def test_all_query_children_are_independent_across_calls_and_instances(self):
        first, second = self.instance(), self.instance()
        result = asyncio.run(queries(first))
        result["algorithms"][0]["knownOptions"].clear()
        next(row for row in result["algorithms"] if row.get("supportedFeatures"))["supportedFeatures"].clear()
        result["options"][0]["targets"].clear()
        result["categories"][0]["knownLayouters"].append("invented")
        for instance in (first, second):
            self.assertEqual(asyncio.run(queries(instance)), expected())

    def test_closed_instance_rejects_all_queries_and_clears_trace(self):
        instance = self.instance()
        self.assertEqual(asyncio.run(queries(instance)), expected())
        instance.terminateWorker()
        for method in (instance.knownLayoutAlgorithms, instance.knownLayoutOptions, instance.knownLayoutCategories):
            with self.assertRaises(ResourceClosedError) as caught:
                asyncio.run(method())
            self.assertEqual((caught.exception.code, caught.exception.path), ("RESOURCE_CLOSED", ""))
        with self.assertRaises(ResourceClosedError):
            asyncio.run(instance.layout({"id": "g"}))
        self.assertEqual(instance.last_trace, [])
        self.assertIsNone(instance.terminateWorker())

    def test_metadata_describes_full_reference_features_without_bounded_native_extensions(self):
        result = asyncio.run(queries(self.instance()))
        algorithm = next(row for row in result["algorithms"] if row["id"] == "org.eclipse.elk.layered")
        self.assertIn("COMPOUND", algorithm["supportedFeatures"])
        self.assertIn("INSIDE_SELF_LOOPS", algorithm["supportedFeatures"])
        self.assertNotIn("native", algorithm)
        by_id = {row["id"]: row for row in result["options"]}
        self.assertEqual(by_id["org.eclipse.elk.randomSeed"]["type"], "INT")
        self.assertEqual(by_id["org.eclipse.elk.padding"]["type"], "OBJECT")
        self.assertTrue(all("native" not in row for row in result["options"]))

    def test_reference_catalogue_denominators_remain_separate(self):
        for kind, count in (("algorithms", 12), ("options", 243), ("categories", 8)):
            self.assertEqual(len(json.loads((ROOT / ("references/metadata/" + kind + ".json")).read_bytes())), count)

    def test_constructor_ignores_unrecognized_provider_selectors_and_rejects_invalid_types(self):
        for values in (["invented"], ["org.eclipse.elk.box"], ["org.eclipse.elk.layered", "unknown", "fixed", "box", "random"]):
            self.assertEqual(asyncio.run(queries(self.instance({"algorithms": values}))), expected("algorithmsEmpty"))
        for values, category, code, path in (([1], OptionValidationError, "INVALID_OPTION_VALUE", "/constructor/algorithms"),
                (None, OptionValidationError, "INVALID_OPTION_VALUE", "/constructor/algorithms"),
                ("layered", OptionValidationError, "INVALID_OPTION_VALUE", "/constructor/algorithms")):
            with self.subTest(values=values), self.assertRaises(category) as caught:
                ELK({"algorithms": values})
            self.assertEqual((caught.exception.code, caught.exception.path), (code, path))

    def test_explicit_worker_fields_fail_without_invoking_user_functions(self):
        called = []
        for key, value in (("workerFactory", lambda: called.append(True)), ("workerUrl", None)):
            with self.assertRaises(UnsupportedWorkerError) as caught:
                ELK({key: value})
            self.assertIsInstance(caught.exception, NotImplementedError)
            self.assertIsInstance(caught.exception, UnsupportedFeatureError)
            self.assertIsInstance(caught.exception, ValidationError)
            self.assertEqual(caught.exception.path, "/constructor/" + key)
        self.assertEqual(called, [])

    def test_unknown_constructor_field_uses_escaped_json_pointer(self):
        with self.assertRaises(UnsupportedFeatureError) as caught:
            ELK({"a/b~c": 1})
        self.assertEqual(caught.exception.path, "/constructor/a~1b~0c")


if __name__ == "__main__":
    unittest.main()
