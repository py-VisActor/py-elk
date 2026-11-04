"""Mutation controls for original-only E07 geometry premises."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "tests/validation")]
from e07_geometry_premise import premises
from layout_checks import geometry
import test_degenerate_layers as degenerate


class E07GeometryTests(unittest.TestCase):
    def ring(self):
        request, observed, policy = degenerate.DegenerateLayerGeometryTests().synthetic_chain(cyclic=True)
        request.update(constructor={},layoutArguments={})
        request["schema"]="py-elk-layout-request/v1"
        request["graph"]["layoutOptions"]={"elk.padding":"[top=0,right=0,bottom=0,left=0]",
                                           "elk.spacing.nodeNode":policy["nodeNode"],
                                           "elk.layered.spacing.nodeNodeBetweenLayers":policy["betweenLayers"]}
        return request, observed, {**policy, "forwardEdges": False,
                                  "rankSeparation": "default-layered-components-v2"}

    def test_original_ring_and_dag_reachability_prove_only_specific_pairs(self):
        request, observed, policy = self.ring()
        self.assertTrue(geometry(request, observed, policy)["passed"])
        request["graph"]["edges"].pop()
        self.assertEqual(len(premises(request)["distinctRanks"]), 3)
        request["graph"]["edges"] = [{"id":"ab", "sources":["a"], "targets":["b"]},
                                      {"id":"ac", "sources":["a"], "targets":["c"]}]
        self.assertNotIn(frozenset(("b","c")), premises(request)["distinctRanks"])

    def test_ring_extras_remove_all_ring_exemptions(self):
        request, _, _ = self.ring()
        for s,t in (("a","a"),("a","b"),("a","c")):
            value=copy.deepcopy(request)
            value["graph"]["edges"].append({"id":"extra", "sources":[s], "targets":[t]})
            self.assertEqual(premises(value)["distinctRanks"],set())

    def test_candidate_ring_cannot_replace_original_topology(self):
        request, observed, policy = self.ring()
        request["graph"]["edges"].append({"id":"loop", "sources":["a"], "targets":["a"]})
        codes={e["code"] for e in geometry(request,observed,policy)["errors"]}
        self.assertIn("same_layer_spacing",codes)
        self.assertIn("model_identity_or_order",codes)

    def test_independent_frames_only_exempt_pairs_in_different_original_components(self):
        request, observed, policy = self.ring()
        request["graph"]["edges"]=[];observed["result"]["edges"]=[]
        self.assertIn("same_layer_spacing",{e["code"] for e in geometry(request,observed,policy)["errors"]})
        policy["layerFrame"]="independent-components-v1"
        self.assertTrue(geometry(request,observed,policy)["passed"])
        request["graph"]["layoutOptions"]={"elk.separateConnectedComponents":False}
        self.assertEqual(geometry(request,observed,policy)["errors"][0]["code"],"layer_frame_premise")

    def test_false_and_invalid_boolean_cannot_claim_independent_frames(self):
        request, observed, policy = self.ring()
        policy["layerFrame"]="independent-components-v1"
        for value in (False,"false",0,1,None,[],"no"):
            request["graph"]["layoutOptions"]={"elk.separateConnectedComponents":value}
            self.assertEqual(geometry(request,observed,policy)["errors"][0]["code"],"layer_frame_premise")
        request["graph"]["layoutOptions"].update({"elk.separateConnectedComponents":"TRUE",
            "elk.padding":"[top=0,right=0,bottom=0,left=0]", "elk.spacing.nodeNode":policy["nodeNode"],
            "elk.layered.spacing.nodeNodeBetweenLayers":policy["betweenLayers"]})
        self.assertTrue(geometry(request,observed,policy)["passed"])

    def test_alias_duplicates_even_equal_and_unknown_strategy_fail_closed(self):
        request,_,_=self.ring()
        for options in ({"elk.direction":"RIGHT","org.eclipse.elk.direction":"RIGHT"},
                        {"direction":"RIGHT"},{"elk.layered.cycleBreaking.strategy":"GREEDY"},
                        {"elk.algorithm":"elk.layered"},{"elk.randomSeed":0}):
            request["graph"]["layoutOptions"]=options
            self.assertIsNone(premises(request))

    def test_replaced_constructor_and_root_override_follow_presence(self):
        request,_,_=self.ring()
        request["constructor"]={"defaultLayoutOptions":{"unknown":"unparsed"}}
        request["layoutArguments"]={"layoutOptions":{}}
        self.assertIsNotNone(premises(request))
        request["layoutArguments"]["layoutOptions"]={"elk.randomSeed":0,"elk.direction":"LEFT"}
        request["graph"]["layoutOptions"]={"elk.randomSeed":17,"elk.direction":"DOWN"}
        self.assertEqual(premises(request)["options"]["direction"],"DOWN")
        request["constructor"]["defaultLayoutOptions"]=None
        self.assertIsNone(premises(request))

    def test_direction_policy_must_match_actual_original_effective_direction(self):
        request,observed,policy=self.ring()
        request["graph"]["layoutOptions"]={"elk.direction":"UP"}
        self.assertEqual(geometry(request,observed,policy)["errors"][0]["code"],"rank_separation_premise")

    def test_arbitrary_scc_equal_edge_count_does_not_gain_ring_lemma(self):
        request,_,_=self.ring()
        request["graph"]["edges"]=[{"id":"ab","sources":["a"],"targets":["b"]},
                                      {"id":"ba","sources":["b"],"targets":["a"]},
                                      {"id":"ac","sources":["a"],"targets":["c"]}]
        self.assertEqual(premises(request)["distinctRanks"],set())

    def test_relaxations_preserve_overlap_endpoint_bounds_and_route_checks(self):
        request,observed,policy=self.ring()
        for before,after in zip(request["graph"]["children"],observed["result"]["children"]):
            before.update(width=10,height=10);after.update(width=10,height=10)
        observed["result"].update(width=5,height=5)
        observed["result"]["edges"][0]["targets"]=["c"]
        codes={e["code"] for e in geometry(request,observed,policy)["errors"]}
        self.assertTrue({"node_overlap","original_endpoint_identity","root_padding_bounds"}<=codes)

    def test_outside_domain_never_returns_partial_exemptions(self):
        request,_,_=self.ring()
        for mutate in (lambda d:d["graph"]["children"][0].update(layoutOptions={"elk.direction":"RIGHT"}),
                       lambda d:d["graph"]["children"][0].update(width=1_000_001),
                       lambda d:d["graph"]["edges"][0].update(targets=["missing"]),
                       lambda d:d["graph"].update(layoutOptions={"elk.padding":"[top=1,left=1,right=1]"}),
                       lambda d:d["layoutArguments"].update(logging=True)):
            value=copy.deepcopy(request);mutate(value);self.assertIsNone(premises(value))

    def test_double_prefix_legacy_endpoint_and_invalid_containers_are_rejected(self):
        request,_,_=self.ring()
        for mutate in (lambda d:d["graph"].update(layoutOptions={"org.eclipse.elk.elk.direction":"RIGHT"}),
                       lambda d:d["graph"]["children"][0].update(ports=None),
                       lambda d:d["graph"]["children"][0].update(children={}),
                       lambda d:d["graph"]["edges"][0].update(layoutOptions=None),
                       lambda d:d["graph"]["edges"][0].update(source="a")):
            value=copy.deepcopy(request);mutate(value);self.assertIsNone(premises(value))

    def test_declared_geometry_limits_cannot_be_weakened(self):
        request,observed,policy=self.ring()
        for key,value in (("padding",dict.fromkeys(("top","right","bottom","left"),1)),
                          ("nodeNode",0),("betweenLayers",1),("componentRectangleGap",0)):
            changed={**policy,key:value}
            self.assertEqual(geometry(request,observed,changed)["errors"][0]["code"],"geometry_option_premise")
