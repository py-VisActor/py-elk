"""E07 independent input selection, byte preservation and conservative bounds."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_e07_suite import build_suite, check_suite, classify_request, plan_suite


def request():
    return {"schema": "py-elk-layout-request/v1", "constructor": {}, "layoutArguments": {},
            "graph": {"id": "root", "children": [{"id": x, "width": 0, "height": 0} for x in "abcd"],
                      "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]},
                                {"id": "cd", "sources": ["c"], "targets": ["d"]}]}}


class E07SuiteTests(unittest.TestCase):
    def test_fixed_denominator_and_positive_inputs_never_promote_runtime(self):
        cases, selected, raw = plan_suite()
        self.assertEqual((selected["master"]["caseCount"], selected["selectedMasterCases"],
                          selected["excludedMasterCases"], selected["projectVariantCount"], len(cases["cases"])),
                         (25, 22, 3, 50, 72))
        self.assertEqual(len(raw), 72)
        self.assertEqual(selected["algorithmSourceGate"], "unverified-for-E07-expansion")
        self.assertEqual(selected["supportStatus"], "PROPOSED_SOURCE_GUARDS_PENDING")
        self.assertIs(type(selected["pythonAlgorithmsVerified"]), int)
        self.assertEqual(selected["pythonAlgorithmsVerified"], 0)
        self.assertTrue(all(row["reasons"] for row in selected["masterCases"] if not row["included"]))

    def test_every_preselected_variant_is_valid_without_mutating_input(self):
        cases, _, raw = plan_suite()
        for case in cases["cases"]:
            item = json.loads(raw[case["request"]]); before = copy.deepcopy(item)
            selected = classify_request(item)
            self.assertTrue(selected["included"], (case["id"], selected))
            self.assertEqual(item, before)
            self.assertEqual(case["geometry"], selected["geometry"])

    def test_real_original_direction_and_component_mode_bind_geometry_policy(self):
        for direction in ("RIGHT", "LEFT", "DOWN", "UP", "UNDEFINED"):
            for separate in (True, False, "TRUE", "false"):
                item = request(); item["graph"]["layoutOptions"] = {
                    "elk.direction": direction, "elk.separateConnectedComponents": separate}
                selected = classify_request(item)
                self.assertTrue(selected["included"])
                self.assertEqual(selected["geometry"]["direction"], "RIGHT" if direction == "UNDEFINED" else direction)
                self.assertEqual("layerFrame" in selected["geometry"], separate in (True, "TRUE"))
                self.assertEqual(selected["geometry"]["rankSeparation"], "default-layered-components-v2")

    def test_bad_aliases_unknown_strategies_or_nonboolean_modes_fail_closed(self):
        for options in ({"elk.direction": "DOWN", "org.eclipse.elk.direction": "DOWN"},
                        {"elk.separateConnectedComponents": 0}, {"elk.edgeRouting": "POLYLINE"},
                        {"elk.randomSeed": 0}, {"elk.layered.cycleBreaking.strategy": "GREEDY"},
                        {"elk.direction": "SIDEWAYS"}, {"elk.spacing.nodeNode": -1}):
            item = request(); item["graph"]["layoutOptions"] = options
            self.assertFalse(classify_request(item)["included"], options)

    def test_call_mapping_replaces_constructor_then_root_overrides_it(self):
        item = request(); item["constructor"]["defaultLayoutOptions"] = {
            "elk.direction": "DOWN", "elk.separateConnectedComponents": False, "elk.randomSeed": 17}
        self.assertEqual(classify_request(item)["geometry"]["direction"], "DOWN")
        item["layoutArguments"]["layoutOptions"] = {}
        self.assertEqual(classify_request(item)["geometry"]["direction"], "RIGHT")
        item["graph"]["layoutOptions"] = {"elk.direction": "UP"}
        self.assertEqual(classify_request(item)["geometry"]["direction"], "UP")

    def test_child_padding_is_a_narrow_source_probe_other_element_semantics_excluded(self):
        for key in ("elk.padding", "org.eclipse.elk.padding"):
            item = request(); item["graph"]["children"][0]["layoutOptions"] = {key: "[top=1,left=3,bottom=5,right=7]"}
            self.assertTrue(classify_request(item)["included"])
        for options in ({"elk.direction": "UP"}, {"elk.padding": {"top": 0, "left": 0, "bottom": 0, "right": 0}},
                        {"elk.padding": "[top=0,left=0,bottom=0,right=0]", "org.eclipse.elk.padding": "[top=0,left=0,bottom=0,right=0]"}):
            item = request(); item["graph"]["children"][0]["layoutOptions"] = options
            self.assertFalse(classify_request(item)["included"])

    def test_scale_and_numeric_budget_count_all_components_and_repeated_edges(self):
        item = request(); item["graph"]["children"] = [{"id": str(i), "width": 1_000_000, "height": 0} for i in range(8)]
        item["graph"]["edges"] = [{"id": "edge-" + str(i), "sources": ["0"], "targets": ["1"]} for i in range(28)]
        self.assertTrue(classify_request(item)["included"])
        item["graph"]["edges"].append({"id": "extra", "sources": ["2"], "targets": ["2"]})
        self.assertFalse(classify_request(item)["included"])
        item = request(); item["graph"]["children"].extend({"id": str(i), "width": 0, "height": 0} for i in range(5))
        self.assertFalse(classify_request(item)["included"])
        for key in ("elk.spacing.nodeNode", "elk.spacing.componentComponent", "elk.layered.spacing.nodeNodeBetweenLayers"):
            item = request(); item["graph"]["layoutOptions"] = {key: 1_000_001}
            self.assertFalse(classify_request(item)["included"])

    def test_structural_geometry_and_registration_rejections_remain_strict(self):
        for where, key in (("root", "x"), ("root", "$H"), ("root", "logging"), ("child", "y"),
                           ("edge", "junctionPoints"), ("edge", "sections")):
            item = request(); target = {"root": item["graph"], "child": item["graph"]["children"][0], "edge": item["graph"]["edges"][0]}[where]
            target[key] = None
            self.assertFalse(classify_request(item)["included"])
        for values in ({"workerUrl": None}, {"algorithms": []}, {"algorithms": ["layered", "stress"]}):
            item = request(); item["constructor"] = values
            self.assertFalse(classify_request(item)["included"])

    def test_master_copy_is_exact_and_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); original = (json.dumps(request(), indent=3) + "\n").replace("\n", "\r\n").encode()
            (base / "request.json").write_bytes(original)
            master = base / "cases.json"; master.write_text(json.dumps({"schema": "py-elk-validation-cases/v1", "cases": [
                {"id": "temp", "request": "request.json", "origin": "project-authored", "expectedOutcome": "returned"}]}), encoding="utf8")
            out = base / "out"; build_suite(out, master=master)
            self.assertEqual((out / "requests/master/temp.json").read_bytes(), original)
            self.assertEqual(check_suite(out, master=master)["selectedMasterCases"], 1)
            with self.assertRaises(FileExistsError): build_suite(out, master=master)
            (out / "requests/master/temp.json").write_bytes(original + b"\n")
            with self.assertRaises(ValueError): check_suite(out, master=master)

    def test_rebound_input_selection_or_geometry_changes_are_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for i, (path, mutate) in enumerate((
                ("selection.json", lambda x: x.update(pythonAlgorithmsVerified=1)),
                ("selection.json", lambda x: x.update(masterCases=[])),
                ("cases.json", lambda x: x["cases"][0]["geometry"].update(direction="UP")),
            )):
                out = base / str(i); build_suite(out); p = out / path; value = json.loads(p.read_bytes()); mutate(value)
                p.write_text(json.dumps(value), encoding="utf8")
                with self.assertRaises(ValueError): check_suite(out)


if __name__ == "__main__":
    unittest.main()
