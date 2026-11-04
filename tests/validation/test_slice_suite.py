"""Independent E04 suite membership/byte controls; no candidate layout runs."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_slice_suite import build_suite, check_suite, classify_request, plan_suite


def request():
    return {"schema": "py-elk-layout-request/v1", "constructor": {}, "layoutArguments": {},
            "graph": {"id": "root", "children": [{"id": "a", "width": 7, "height": 3},
                                                       {"id": "b", "width": 11, "height": 5}],
                      "edges": [{"id": "edge", "sources": ["a"], "targets": ["b"]}]}}


class SliceSuiteTests(unittest.TestCase):
    def fixture(self, base):
        directory = base / "master"
        directory.mkdir()
        raw = (json.dumps(request(), indent=3) + "\n").replace("\n", "\r\n").encode()
        (directory / "request.json").write_bytes(raw)
        master = directory / "cases.json"
        master.write_text(json.dumps({"schema": "py-elk-validation-cases/v1", "cases": [
            {"id": "temp-master", "request": "request.json", "origin": "project-authored", "expectedOutcome": "returned", "geometry": {"from": "test-master"}}]}), encoding="utf-8")
        return master, raw

    def test_all_25_master_cases_are_accounted_for_and_only_five_selected(self):
        cases, selected, raw = plan_suite()
        self.assertEqual(selected["master"]["caseCount"], 25)
        self.assertEqual(len(selected["masterCases"]), 25)
        self.assertEqual(selected["selectedMasterCases"], 5)
        self.assertEqual(selected["excludedMasterCases"], 20)
        included = {c["id"] for c in selected["masterCases"] if c["included"]}
        self.assertEqual(included, {"layered-empty", "layered-singleton", "layered-chain", "layered-zero-size", "options-explicit-empty-replaces-default"})
        self.assertTrue(all(c["reasons"] for c in selected["masterCases"] if not c["included"]))
        self.assertEqual(selected["projectVariantCount"], 16)
        self.assertEqual(selected["suiteCaseCount"], 21)
        self.assertEqual(len(cases["cases"]), len(raw))
        self.assertEqual(selected["pythonAlgorithmsVerified"], 0)
        self.assertEqual(selected["oracleStatus"], "CAPTURE_SEPARATELY")

    def test_master_request_bytes_include_crlf_and_are_not_reserialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            master, original = self.fixture(base)
            built = base / "new-suite"
            build_suite(built, master=master)
            copied = built / "requests/master/temp-master.json"
            self.assertEqual(copied.read_bytes(), original)
            self.assertIn(b"\r\n", copied.read_bytes())
            self.assertEqual(check_suite(built, master=master)["master"]["caseCount"], 1)

    def test_new_output_rule_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            master, _ = self.fixture(base)
            target = base / "suite"
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_bytes(b"keep-existing")
            with self.assertRaises(FileExistsError):
                build_suite(target, master=master)
            self.assertEqual(marker.read_bytes(), b"keep-existing")

    def test_requests_and_reasons_do_not_mutate_during_classification(self):
        item = request()
        item["graph"]["business"] = {"$H": False, "error": {"stack": "keep"}, "null": None}
        before = copy.deepcopy(item)
        self.assertTrue(classify_request(item)["included"])
        self.assertEqual(item, before)

    def test_topology_rejects_fork_join_parallel_cycle_self_and_disconnected(self):
        links = [([("a", "b"), ("a", "c")], 3), ([("a", "c"), ("b", "c")], 3),
                 ([("a", "b"), ("a", "b")], 2), ([("a", "b"), ("b", "a")], 2),
                 ([("a", "a")], 1), ([("a", "b"), ("c", "d")], 4),
                 ([("a", "b"), ("b", "a")], 3)]
        for pairs, count in links:
            with self.subTest(pairs=pairs, count=count):
                item = request()
                item["graph"]["children"] = [{"id": name, "width": 1, "height": 1} for name in "abcd"[:count]]
                item["graph"]["edges"] = [{"id": "e" + str(i), "sources": [a], "targets": [b]} for i, (a, b) in enumerate(pairs)]
                result = classify_request(item)
                self.assertFalse(result["included"])
                self.assertTrue(result["reasons"])

    def test_non_right_directions_are_exclusions_even_for_empty_graph(self):
        for direction in ("LEFT", "DOWN", "UP"):
            item = request()
            item["graph"].update(children=[], edges=[], layoutOptions={"elk.direction": direction})
            decision = classify_request(item)
            self.assertFalse(decision["included"])
            self.assertIn("direction-outside-slice", {r["code"] for r in decision["reasons"]})

    def test_empty_call_replaces_constructor_before_local_scope(self):
        item = request()
        item["constructor"] = {"defaultLayoutOptions": {"elk.direction": "DOWN"}}
        self.assertFalse(classify_request(item)["included"])
        item["layoutArguments"] = {"layoutOptions": {}}
        selected = classify_request(item)
        self.assertTrue(selected["included"])
        self.assertEqual(selected["directionOption"], "UNDEFINED")
        item["graph"]["layoutOptions"] = {"elk.direction": "RIGHT"}
        self.assertTrue(classify_request(item)["included"])

    def test_advanced_shapes_and_element_configuration_are_not_selected(self):
        for key, value in (("ports", [{"id": "p"}]), ("labels", [{"text": "label"}]),
                           ("children", [{"id": "nested"}]), ("layoutOptions", {"elk.direction": "RIGHT"})):
            item = request()
            item["graph"]["children"][0][key] = value
            self.assertFalse(classify_request(item)["included"])

    def test_identity_dimension_and_endpoint_types_fail_closed(self):
        for field, value in (("id", 1), ("id", False), ("width", True), ("width", -1),
                             ("width", float("inf")), ("height", None)):
            item = request()
            item["graph"]["children"][0][field] = value
            self.assertFalse(classify_request(item)["included"])
        item = request()
        del item["graph"]["children"][0]["height"]
        self.assertFalse(classify_request(item)["included"])
        item = request()
        item["graph"]["edges"][0]["targets"] = ["missing"]
        self.assertFalse(classify_request(item)["included"])

    def test_unseeded_components_diagnostics_and_worker_are_excluded(self):
        alterations = [lambda r: r["graph"].update(layoutOptions={"elk.randomSeed": 0}),
                       lambda r: r["graph"].update(layoutOptions={"elk.separateConnectedComponents": False}),
                       lambda r: r["layoutArguments"].update(logging=True),
                       lambda r: r["layoutArguments"].update(measureExecutionTime=True),
                       lambda r: r["constructor"].update(workerUrl=None),
                       lambda r: r["constructor"].update(algorithms=[])]
        for alter in alterations:
            item = request()
            alter(item)
            self.assertFalse(classify_request(item)["included"])

    def test_check_rejects_request_byte_drift_even_when_json_is_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); master, _ = self.fixture(base); target = base / "suite"
            build_suite(target, master=master)
            request_path = target / "requests/master/temp-master.json"
            request_path.write_bytes(request_path.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                check_suite(target, master=master)

    def test_final_source_scope_enforces_four_nodes_and_numeric_upper_boundary(self):
        item = request()
        item["graph"]["children"] = [{"id": str(i), "width": 1_000_000, "height": 0} for i in range(4)]
        item["graph"]["edges"] = [{"id": "e" + str(i), "sources": [str(i)], "targets": [str(i + 1)]} for i in range(3)]
        self.assertTrue(classify_request(item)["included"])
        item["graph"]["children"].append({"id": "4", "width": 1, "height": 1})
        item["graph"]["edges"].append({"id": "e3", "sources": ["3"], "targets": ["4"]})
        self.assertFalse(classify_request(item)["included"])
        item = request()
        item["graph"]["children"][0]["width"] = 1_000_001
        self.assertFalse(classify_request(item)["included"])
        for key in ("elk.spacing.nodeNode", "elk.layered.spacing.nodeNodeBetweenLayers", "elk.spacing.componentComponent"):
            item = request(); item["graph"]["layoutOptions"] = {key: 1_000_000}
            self.assertTrue(classify_request(item)["included"])
            item["graph"]["layoutOptions"][key] = 1_000_001
            self.assertFalse(classify_request(item)["included"])
        for value, expected in ((1_000_000, True), (1_000_001, False)):
            item = request()
            item["graph"]["layoutOptions"] = {"elk.padding": "[top=" + str(value) + ",left=0,bottom=0,right=0]"}
            self.assertEqual(classify_request(item)["included"], expected)

    def test_effective_padding_mapping_is_excluded_but_replaced_values_are_not_parsed(self):
        padding = {"top": 1, "right": 2, "bottom": 3, "left": 4}
        for key in ("padding", "elk.padding", "org.eclipse.elk.padding"):
            for scope in ("constructor", "call", "local"):
                item = request()
                target = {"constructor": item["constructor"].setdefault("defaultLayoutOptions", {}),
                          "call": item["layoutArguments"].setdefault("layoutOptions", {}),
                          "local": item["graph"].setdefault("layoutOptions", {})}[scope]
                # Empty call would replace constructor, so remove it in that case.
                if scope == "constructor":
                    item["layoutArguments"].clear()
                target[key] = copy.deepcopy(padding)
                before = copy.deepcopy(item)
                self.assertFalse(classify_request(item)["included"])
                self.assertEqual(item, before)
        item = request()
        item["constructor"] = {"defaultLayoutOptions": {"elk.padding": padding}}
        item["layoutArguments"] = {"layoutOptions": {}}
        self.assertTrue(classify_request(item)["included"])
        item["layoutArguments"] = {"layoutOptions": {"elk.padding": padding}}
        item["graph"]["layoutOptions"] = {"elk.padding": "[top=1,right=2,bottom=3,left=4]"}
        self.assertTrue(classify_request(item)["included"])

    def test_existing_geometry_is_excluded_without_removing_it(self):
        for place, key, value in (("root", "width", 12), ("root", "x", 0),
                                   ("node", "x", 0), ("edge", "sections", []),
                                   ("edge", "sourcePoint", {}), ("edge", "targetPoint", {})):
            item = request()
            element = {"root": item["graph"], "node": item["graph"]["children"][0], "edge": item["graph"]["edges"][0]}[place]
            element[key] = value
            before = copy.deepcopy(item)
            self.assertFalse(classify_request(item)["included"])
            self.assertEqual(item, before)

    def test_legacy_properties_and_unknown_execution_do_not_bypass_direction_scope(self):
        alterations = [lambda r: r["graph"].update(properties={"elk.direction": "DOWN"}),
                       lambda r: r["graph"]["children"][0].update(properties={}),
                       lambda r: r["graph"]["edges"][0].update(properties=None),
                       lambda r: r["graph"]["edges"][0].update(container="root"),
                       lambda r: r["constructor"].update(unknownParameter=True),
                       lambda r: r["layoutArguments"].update(unknownParameter=True),
                       lambda r: r["constructor"].update(algorithms=["layered", "stress"]),
                       lambda r: r["constructor"].update(algorithms=["layered", "layered"])]
        for alter in alterations:
            item = request(); alter(item); before = copy.deepcopy(item)
            self.assertFalse(classify_request(item)["included"])
            self.assertEqual(item, before)
        item = request()
        item["graph"]["business"] = {"properties": {"elk.direction": "DOWN"}}
        item["constructor"] = {"algorithms": ["layered"]}
        self.assertTrue(classify_request(item)["included"])

    def test_known_root_logging_and_direct_shape_hash_branches_are_excluded(self):
        for value in (None, False, 0, "user-value", []):
            for place in ("root", "child"):
                item = request()
                shape = item["graph"] if place == "root" else item["graph"]["children"][0]
                shape["$H"] = value
                self.assertFalse(classify_request(item)["included"])
            item = request(); item["graph"]["logging"] = value
            self.assertFalse(classify_request(item)["included"])
        item = request()
        item["graph"]["business"] = {"$H": False, "error": {"stack": "keep"}, "logging": None}
        self.assertTrue(classify_request(item)["included"])

    def test_check_rejects_false_claims_denominator_reason_geometry_and_extra_request(self):
        alterations = [lambda d: d["master"].update(caseCount=5),
                       lambda d: d.update(pythonAlgorithmsVerified=1),
                       lambda d: d["masterCases"][0].update(included=False)]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); master, _ = self.fixture(base)
            for index, alter in enumerate(alterations):
                target = base / str(index); build_suite(target, master=master)
                path = target / "selection.json"; doc = json.loads(path.read_bytes()); alter(doc)
                path.write_text(json.dumps(doc), encoding="utf-8")
                with self.assertRaises(ValueError):check_suite(target, master=master)
            target = base / "geometry"; build_suite(target, master=master)
            path = target / "cases.json"; doc = json.loads(path.read_bytes())
            doc["cases"][1]["geometry"]["forwardEdges"] = 1
            path.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):check_suite(target, master=master)
            target = base / "extra"; build_suite(target, master=master)
            (target / "requests/unlisted.json").write_bytes(b"{}")
            with self.assertRaises(ValueError):check_suite(target, master=master)

    def test_master_case_identity_and_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); master, _ = self.fixture(base)
            doc = json.loads(master.read_bytes()); doc["cases"].append(copy.deepcopy(doc["cases"][0]))
            master.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):plan_suite(master)
            doc["cases"].pop(); doc["cases"][0]["request"] = "../outside.json"
            (base / "outside.json").write_text(json.dumps(request()), encoding="utf-8")
            master.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):plan_suite(master)


if __name__ == "__main__":
    unittest.main()
