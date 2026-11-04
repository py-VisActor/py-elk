"""Independent proposed E06 input domain and byte drift; no layout implementation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_e06_suite import build_suite, check_suite, classify_request, plan_suite


def request():
    return {"schema": "py-elk-layout-request/v1", "constructor": {}, "layoutArguments": {},
            "graph": {"id": "root", "children": [{"id": name, "width": 7, "height": 3} for name in "abc"],
                      "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]},
                                {"id": "ac", "sources": ["a"], "targets": ["c"]}]}}


class E06SuiteTests(unittest.TestCase):
    def fixture(self, base):
        master = base / "master"
        master.mkdir()
        raw = (json.dumps(request(), indent=3) + "\n").replace("\n", "\r\n").encode()
        (master / "request.json").write_bytes(raw)
        path = master / "cases.json"
        path.write_text(json.dumps({"schema": "py-elk-validation-cases/v1", "cases": [
            {"id": "temporary-fork", "request": "request.json", "origin": "project-authored", "expectedOutcome": "returned", "geometry": {"test": "master"}}]}), encoding="utf-8")
        return path, raw

    def test_all_master_denominators_and_proposed_status_are_explicit(self):
        cases, selected, raw = plan_suite()
        self.assertEqual(selected["master"]["caseCount"], 25)
        self.assertEqual(len(selected["masterCases"]), 25)
        self.assertEqual(selected["selectedMasterCases"], 15)
        self.assertEqual(selected["excludedMasterCases"], 10)
        expected = {"layered-empty", "layered-singleton", "layered-chain", "layered-zero-size", "options-explicit-empty-replaces-default",
                    "layered-fork", "layered-join", "layered-diamond-right", "layered-long-edge", "layered-unequal-sizes", "layered-custom-spacing", "options-full-ids", "layered-cycle", "layered-self-loop", "layered-parallel-edges"}
        self.assertEqual({c["id"] for c in selected["masterCases"] if c["included"]}, expected)
        self.assertTrue(all(c["reasons"] for c in selected["masterCases"] if not c["included"]))
        self.assertEqual(selected["supportStatus"], "PROPOSED_SOURCE_GUARDS_PENDING")
        self.assertEqual(selected["algorithmSourceGate"], "unverified-for-E06-expansion")
        self.assertEqual(selected["projectVariantCount"], 37)
        self.assertEqual(selected["suiteCaseCount"], 52)
        self.assertEqual(len(cases["cases"]), len(raw))
        self.assertIs(type(selected["pythonAlgorithmsVerified"]), int)
        self.assertEqual(selected["pythonAlgorithmsVerified"], 0)

    def test_fork_join_multi_source_skip_and_permuted_dags_are_preparation_inputs(self):
        cases, _, raw = plan_suite()
        for case in cases["cases"]:
            item = json.loads(raw[case["request"]])
            before = copy.deepcopy(item)
            self.assertTrue(classify_request(item)["included"], case["id"])
            self.assertEqual(item, before)
        self.assertEqual(max(len(json.loads(r)["graph"].get("children", [])) for r in raw.values()), 8)

    def test_cycles_selfloops_parallel_are_preparation_only_but_disconnected_hyperedges_excluded(self):
        for links in ([('a', 'b'), ('b', 'c'), ('c', 'a')], [('a', 'a'), ('a', 'b'), ('b', 'c')],
                      [('a', 'b'), ('a', 'b'), ('b', 'c')]):
            item = request()
            item['graph']['edges'] = [{'id': 'e'+str(i), 'sources': [a], 'targets': [b]} for i, (a, b) in enumerate(links)]
            before = copy.deepcopy(item)
            selected = classify_request(item)
            self.assertTrue(selected['included'], selected)
            self.assertEqual(item, before)
            self.assertEqual(selected['geometry']['forwardEdges'], links[-1] == ('b', 'c') and links[0] != ('a', 'a'))
        item = request(); item['graph']['edges'].pop()
        self.assertFalse(classify_request(item)['included'])
        item = request(); item['graph']['edges'][0]['targets'] = ['b', 'c']
        self.assertFalse(classify_request(item)['included'])

    def test_total_edge_bound_counts_loops_and_repeated_endpoints(self):
        for links in ([('a', 'b')] * 27 + [('b', 'c')], [('a', 'a')] * 26 + [('a', 'b'), ('b', 'c')]):
            item = request()
            item['graph']['edges'] = [{'id': 'edge-'+str(i), 'sources': [a], 'targets': [b]} for i, (a, b) in enumerate(links)]
            selected = classify_request(item)
            self.assertTrue(selected['included'], selected)
            self.assertEqual(selected['topology']['totalEdges'], 28)
            item['graph']['edges'].append({'id': 'edge-28', 'sources': ['a'], 'targets': ['a']})
            self.assertFalse(classify_request(item)['included'])

    def test_rank_marker_requires_original_default_simple_ring_without_extra_edges(self):
        item = request()
        item['graph']['edges'] = [{'id': 'e'+str(i), 'sources': [a], 'targets': [b]}
                                  for i, (a, b) in enumerate([('a', 'b'), ('b', 'c'), ('c', 'a')])]
        before = copy.deepcopy(item)
        selected = classify_request(item)
        self.assertEqual(selected['geometry']['rankSeparation'], 'default-greedy-simple-ring-v1')
        self.assertFalse(selected['geometry']['forwardEdges'])
        self.assertEqual(item, before)
        for extra in ({'id': 'loop', 'sources': ['a'], 'targets': ['a']},
                      {'id': 'duplicate', 'sources': ['a'], 'targets': ['b']},
                      {'id': 'chord', 'sources': ['a'], 'targets': ['c']}):
            changed = copy.deepcopy(item); changed['graph']['edges'].append(extra)
            self.assertTrue(classify_request(changed)['included'])
            self.assertNotIn('rankSeparation', classify_request(changed)['geometry'])
        for options in ({'elk.randomSeed': 0}, {'elk.layered.cycleBreaking.strategy': 'DEPTH_FIRST'},
                        {'elk.layered.layering.strategy': 'LONGEST_PATH'}, {'elk.direction': 'DOWN'}):
            changed = copy.deepcopy(item); changed['graph']['layoutOptions'] = options
            self.assertFalse(classify_request(changed)['included'])

    def test_two_node_ring_is_supported_but_two_disjoint_rings_cannot_get_marker(self):
        item = request(); item['graph']['children'] = item['graph']['children'][:2]
        item['graph']['edges'] = [{'id': 'ab', 'sources': ['a'], 'targets': ['b']},
                                  {'id': 'ba', 'sources': ['b'], 'targets': ['a']}]
        self.assertEqual(classify_request(item)['geometry']['rankSeparation'], 'default-greedy-simple-ring-v1')
        item['graph']['children'] += [{'id': name, 'width': 0, 'height': 0} for name in ('c', 'd')]
        item['graph']['edges'] += [{'id': 'cd', 'sources': ['c'], 'targets': ['d']},
                                   {'id': 'dc', 'sources': ['d'], 'targets': ['c']}]
        selected = classify_request(item)
        self.assertFalse(selected['included'])
        self.assertNotIn('rankSeparation', selected['geometry'])

    def test_identity_size_and_endpoint_invalid_values_fail_closed(self):
        for field, value in (("id", False), ("id", 1), ("id", ""), ("width", False), ("width", -1),
                             ("height", None), ("width", float("inf")), ("height", float("nan"))):
            item = request(); item["graph"]["children"][0][field] = value
            self.assertFalse(classify_request(item)["included"])
        item = request(); del item["graph"]["children"][0]["width"]
        self.assertFalse(classify_request(item)["included"])
        item = request(); item["graph"]["edges"][0]["targets"] = ["missing"]
        self.assertFalse(classify_request(item)["included"])

    def test_proposed_node_and_magnitude_bounds_are_not_unbounded_claims(self):
        item = request()
        item["graph"]["children"] = [{"id": str(i), "width": 1_000_000, "height": 0} for i in range(8)]
        item["graph"]["edges"] = [{"id": "edge-" + str(i), "sources": [str(i)], "targets": [str(i + 1)]} for i in range(7)]
        self.assertTrue(classify_request(item)["included"])
        item["graph"]["children"].append({"id": "8", "width": 1, "height": 1})
        item["graph"]["edges"].append({"id": "edge-7", "sources": ["7"], "targets": ["8"]})
        self.assertFalse(classify_request(item)["included"])
        for field in ("width", "height"):
            item = request(); item["graph"]["children"][0][field] = 1_000_001
            self.assertFalse(classify_request(item)["included"])
        for key in ("elk.spacing.nodeNode", "elk.layered.spacing.nodeNodeBetweenLayers", "elk.spacing.componentComponent"):
            item = request(); item["graph"]["layoutOptions"] = {key: 1_000_001}
            self.assertFalse(classify_request(item)["included"])

    def test_directions_modes_registration_and_diagnostics_remain_outside_proposal(self):
        for options in ({"elk.direction": "LEFT"}, {"elk.direction": "DOWN"}, {"elk.direction": "UP"},
                        {"elk.randomSeed": 0}, {"elk.separateConnectedComponents": False}, {"elk.edgeRouting": "POLYLINE"}):
            item = request(); item["graph"]["layoutOptions"] = options
            self.assertFalse(classify_request(item)["included"])
        for container, key, value in (("constructor", "algorithms", []), ("constructor", "algorithms", ["layered", "stress"]),
                                      ("constructor", "workerUrl", None), ("layoutArguments", "logging", 0),
                                      ("layoutArguments", "measureExecutionTime", True), ("layoutArguments", "unknown", False)):
            item = request(); item[container][key] = value
            self.assertFalse(classify_request(item)["included"])

    def test_existing_geometry_shape_hash_and_root_logging_use_presence(self):
        for where, keys in (("root", ("x", "y", "width", "height", "$H", "logging", "properties")),
                            ("child", ("x", "y", "$H", "properties")),
                            ("edge", ("sections", "junctionPoints", "bendPoints", "startPoint", "endPoint", "sourcePoint", "targetPoint", "container", "properties"))):
            for key in keys:
                for value in (None, False, 0, [], {}):
                    item = request()
                    target = {"root": item["graph"], "child": item["graph"]["children"][0], "edge": item["graph"]["edges"][0]}[where]
                    target[key] = value; before = copy.deepcopy(item)
                    self.assertFalse(classify_request(item)["included"], (where, key, value))
                    self.assertEqual(item, before)

    def test_business_fields_and_empty_structural_containers_are_preserved(self):
        item = request()
        item["graph"]["business"] = {"$H": False, "properties": {"elk.direction": "DOWN"}, "error": {"stack": "keep"}}
        item["graph"]["children"][0].update(children=[], edges=[], ports=[], labels=[], layoutOptions={})
        before = copy.deepcopy(item)
        self.assertTrue(classify_request(item)["included"])
        self.assertEqual(item, before)

    def test_nonempty_element_options_ports_labels_and_hierarchy_are_excluded(self):
        for key, value in (("layoutOptions", {"elk.direction": "RIGHT"}), ("ports", [{"id": "p"}]),
                           ("labels", [{"text": "given"}]), ("children", [{"id": "nested"}])):
            item = request(); item["graph"]["children"][0][key] = value
            self.assertFalse(classify_request(item)["included"])

    def test_padding_uses_effective_raw_type_and_option_precedence(self):
        padding = {"top": 1, "left": 2, "bottom": 3, "right": 4}
        item = request(); item["graph"]["layoutOptions"] = {"elk.padding": padding}
        self.assertFalse(classify_request(item)["included"])
        item = request(); item["constructor"] = {"defaultLayoutOptions": {"elk.padding": padding, "elk.direction": "DOWN"}}
        item["layoutArguments"] = {"layoutOptions": {}}
        self.assertTrue(classify_request(item)["included"])
        item["layoutArguments"] = {"layoutOptions": {"elk.padding": padding}}
        item["graph"]["layoutOptions"] = {"elk.padding": "[top=1,left=2,bottom=3,right=4]"}
        self.assertTrue(classify_request(item)["included"])

    def test_original_master_bytes_are_copied_without_reserialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); master, original = self.fixture(base); built = base / "new"
            build_suite(built, master=master)
            self.assertEqual((built / "requests/master/temporary-fork.json").read_bytes(), original)
            self.assertEqual(check_suite(built, master=master)["master"]["caseCount"], 1)

    def test_output_never_overwrites_existing_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); master, _ = self.fixture(base); built = base / "new"; built.mkdir()
            (built / "keep").write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                build_suite(built, master=master)
            self.assertEqual((built / "keep").read_bytes(), b"keep")

    def test_equal_json_with_changed_original_bytes_is_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); master, _ = self.fixture(base); built = base / "new"; build_suite(built, master=master)
            path = built / "requests/master/temporary-fork.json"; path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                check_suite(built, master=master)

    def test_rebound_selection_claims_and_geometry_boolean_tampering_are_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); master, _ = self.fixture(base)
            for i, mutate in enumerate((lambda d: d.update(pythonAlgorithmsVerified=1),
                                         lambda d: d.update(algorithmSourceGate="verified"),
                                         lambda d: d["master"].update(caseCount=0))):
                built = base / str(i); build_suite(built, master=master); path = built / "selection.json"
                doc = json.loads(path.read_bytes()); mutate(doc); path.write_text(json.dumps(doc), encoding="utf-8")
                with self.assertRaises(ValueError):check_suite(built, master=master)
            built = base / "geometry"; build_suite(built, master=master); path = built / "cases.json"
            doc = json.loads(path.read_bytes()); doc["cases"][1]["geometry"]["forwardEdges"] = 1; path.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):check_suite(built, master=master)

    def test_extra_request_invalid_master_id_and_path_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); master, _ = self.fixture(base); built = base / "new"; build_suite(built, master=master)
            (built / "requests/extra.json").write_bytes(b"{}")
            with self.assertRaises(ValueError):check_suite(built, master=master)
            doc = json.loads(master.read_bytes()); doc["cases"][0]["request"] = "../outside.json"
            (base / "outside.json").write_text(json.dumps(request()), encoding="utf-8"); master.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):plan_suite(master)


if __name__ == "__main__":
    unittest.main()
