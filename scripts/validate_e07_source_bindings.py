"""Validate fixed E07 source/review bindings; never approve or execute layout.

Offline mode uses versioned evidence only. --with-upstream verifies original
Git/npm bytes, LF spans, UTF16 functions and literal symbols/call sites too.
Neither mode proves mathematical equivalence or accepts the Python runtime.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from layout_checks import ROOT, contained, load, sha256, write
from source_read_cache import readonly_source_check
from validate_e04_source_bindings import edge_records, span_records, validate_canonical, validate_span_shape, walk
from validate_e05_source_bindings import (BASELINE, ENCODING, canonical_sha, digest, exact_zero,
                                         json_pointer, nonempty, require, validate_function_line_alignment)
import validate_e06_source_bindings as base

DOCUMENTS = {lane: f"references/e07-source-components-{lane}.json" for lane in "ABR"}
MANIFEST = "references/e07-component-approvals.json"
SCOPE = "docs/decisions/0006-e07-directions-components.md"
FINAL_COMPONENT_IDS = {
    "A": {"direction:mirror-x", "direction:mirror-y", "direction:transpose", "phase:NETWORK_SIMPLEX"},
    "B": {"components:split", "components:simple-row-combine", "components:layout-finalization"},
    "R": base.ALL_COMPONENT_IDS - {"phase:NETWORK_SIMPLEX"},
}
ALL_COMPONENT_IDS = set().union(*FINAL_COMPONENT_IDS.values())
LICENSES = {**base.LICENSES, "src/pyelk/_licenses/NOTICE-E07.md":
            "fe579f603786b6813ace273cd02536db139bbf97bb7b951454a98854ed7870ef"}
INHERITED = {**base.INHERITED,
    "references/e06-component-approvals.json": "f5cf8065351189ea68eacd9d1733afc84d756d3ad45c9c0486ebfa135a94b13e",
    "references/e06-source-components-A.json": "375d8c5154897e884cd142b328872b1c11881407e0b6ff0a613d5d8cb3c50f54",
    "references/e06-source-components-B.json": "f29eff99bc8548b3f2861a7052f19b19a76907a17ae1eed57ae37acb3f174bfd",
    "references/e06-source-components-R.json": "d48ccd799ff351f8075566da9dd9a3c588233d67240f9cd3c6b8b09b522ef26f",
    base.SCOPE: "2343855ce1ce902eb4d45a273f799f16c6d92194a602f22bf07fb6b7c429f13c",
}
COMMON_CONTEXT_SHA = "0650361b6cbef5e1ee605d02b8653799dd5bf9ae9400e34e48b5004b78336b4d"
CONTEXT_SHA = {"A": "9f62efadb94027c15791504dc745e62c1078bed439cfdc827aec55636b4087b5",
               "B": "4f15ad0720f9931681f92952ad05fa891b2d740307af0c00b5a311c1b6db9b09",
               "R": "e0ba4fa63dc3a2e2ba4e3ec55ac8771d669423bf56c8b822b8811c44de3a3669"}
NS_CONTEXT_SHA = "a52deb9ab3cb3fddf649d55e282988927ca7d5fe072dab1973a31f516e50b143"
SHARED_DIRECTION_PROOFS = ("DIR-CFG-REAL-MODES-AND-ORDER", "DIR-HOST-MUTABLE-DEFAULTS",
                           "DIR-HOST-SIDE-ANCHOR", "DIR-GUARDED-LABELS-EXTERNAL-OPTIONS")


REQUIRED_PROOF_IDS = {'direction:mirror-x': ('DIR-X-LITERAL-DATAFLOW',), 'direction:mirror-y': ('DIR-Y-LITERAL-DATAFLOW',), 'direction:transpose': ('DIR-T-LITERAL-DATAFLOW',), 'phase:NETWORK_SIMPLEX': ('NS7-G1-REAL-COMPONENT-DRIVER', 'NS-G2-FEASIBLE-TIGHT-TREE', 'NS-G3-CUT-EXCHANGE', 'NS-G4-NORMALIZE-BALANCE', 'NS-G5-PHASE-NUMERIC-BOUND', 'NS-G6-SPLIT-SCALE', 'NS7-G2-PREVIOUS-FILLING-DEF-USE', 'NS7-G3-DIRECTION-AND-NO-RNG', 'NS7-G4-GEOMETRY-RANK-SEPARATION', 'NS7-HOST-CALLER-SEPARATION'), 'components:split': ('CP-SPLIT1', 'CP-SPLIT2', 'CP-SPLIT3', 'CP-SPLIT4'), 'components:simple-row-combine': ('CP-COMBINE1', 'CP-COMBINE2', 'CP-COMBINE3', 'CP-COMBINE4'), 'components:layout-finalization': ('CP-FINAL1', 'CP-FINAL2', 'CP-FINAL3'), 'graph:edge-reversal': ('REV7-DOMAIN',), 'phase:GREEDY': ('GR7-DISCONNECTED-ORDER',), 'intermediate:ReversedEdgeRestorer': ('E07-intermediate-ReversedEdgeRestorer',), 'intermediate:LongEdgeSplitter': ('E07-intermediate-LongEdgeSplitter',), 'intermediate:LongEdgeJoiner': ('E07-intermediate-LongEdgeJoiner',), 'intermediate:SelfLoopPreProcessor': ('E07-intermediate-SelfLoopPreProcessor',), 'intermediate:SelfLoopPortRestorer': ('E07-intermediate-SelfLoopPortRestorer',), 'intermediate:SelfLoopRouter': ('E07-intermediate-SelfLoopRouter',), 'intermediate:SelfLoopPostProcessor': ('E07-intermediate-SelfLoopPostProcessor',), 'intermediate:EdgeAndLayerConstraintEdgeReverser': ('E07-intermediate-EdgeAndLayerConstraintEdgeReverser',), 'intermediate:LayerConstraintPreprocessor': ('E07-intermediate-LayerConstraintPreprocessor',), 'intermediate:LayerConstraintPostprocessor': ('E07-intermediate-LayerConstraintPostprocessor',), 'intermediate:PortSideProcessor': ('E07-intermediate-PortSideProcessor',), 'intermediate:PortListSorter': ('E07-intermediate-PortListSorter',), 'intermediate:InLayerConstraintProcessor': ('E07-intermediate-InLayerConstraintProcessor',), 'intermediate:InnermostNodeMarginCalculator': ('E07-intermediate-InnermostNodeMarginCalculator',), 'intermediate:LayerSizeAndGraphHeightCalculator': ('E07-intermediate-LayerSizeAndGraphHeightCalculator',), 'intermediate:EndLabelSorter': ('E07-intermediate-EndLabelSorter',), 'intermediate:LabelAndNodeSizeProcessor': ('E07-intermediate-LabelAndNodeSizeProcessor',), 'phase:LAYER_SWEEP_BARYCENTER': ('E07-phase-LAYER-SWEEP-BARYCENTER',), 'phase:LAYER_SWEEP_GREEDY_SWITCH': ('E07-phase-LAYER-SWEEP-GREEDY-SWITCH',), 'phase:BRANDES_KOEPF': ('E07-phase-BRANDES-KOEPF',), 'phase:ORTHOGONAL': ('E07-phase-ORTHOGONAL',), 'import:json-to-layered': ('E07-import-json-to-layered',), 'export:layered-to-json': ('E07-export-layered-to-json',), 'pipeline:default-processor-configuration': ('E07-pipeline-default-processor-configuration',)}
REQUIRED_DEPENDENCIES = {'direction:mirror-x': (), 'direction:mirror-y': (), 'direction:transpose': (), 'phase:NETWORK_SIMPLEX': ('phase:GREEDY',), 'components:split': (), 'components:simple-row-combine': (), 'components:layout-finalization': (), 'graph:edge-reversal': (), 'phase:GREEDY': ('graph:edge-reversal',), 'intermediate:ReversedEdgeRestorer': ('graph:edge-reversal',), 'intermediate:LongEdgeSplitter': ('phase:NETWORK_SIMPLEX', 'graph:edge-reversal'), 'intermediate:LongEdgeJoiner': ('intermediate:LongEdgeSplitter', 'intermediate:ReversedEdgeRestorer'), 'intermediate:SelfLoopPreProcessor': (), 'intermediate:SelfLoopPortRestorer': ('intermediate:SelfLoopPreProcessor',), 'intermediate:SelfLoopRouter': ('intermediate:SelfLoopPreProcessor',), 'intermediate:SelfLoopPostProcessor': ('intermediate:SelfLoopPreProcessor',), 'intermediate:EdgeAndLayerConstraintEdgeReverser': (), 'intermediate:LayerConstraintPreprocessor': (), 'intermediate:LayerConstraintPostprocessor': (), 'intermediate:PortSideProcessor': ('intermediate:LongEdgeSplitter',), 'intermediate:PortListSorter': ('intermediate:PortSideProcessor',), 'intermediate:InLayerConstraintProcessor': (), 'intermediate:InnermostNodeMarginCalculator': (), 'intermediate:LayerSizeAndGraphHeightCalculator': (), 'intermediate:EndLabelSorter': (), 'intermediate:LabelAndNodeSizeProcessor': ('direction:transpose', 'intermediate:SelfLoopPortRestorer', 'intermediate:PortListSorter'), 'phase:LAYER_SWEEP_BARYCENTER': ('phase:NETWORK_SIMPLEX', 'intermediate:LongEdgeSplitter', 'intermediate:SelfLoopPreProcessor', 'intermediate:PortListSorter'), 'phase:LAYER_SWEEP_GREEDY_SWITCH': ('phase:LAYER_SWEEP_BARYCENTER',), 'phase:BRANDES_KOEPF': ('phase:LAYER_SWEEP_GREEDY_SWITCH', 'intermediate:SelfLoopRouter', 'intermediate:LabelAndNodeSizeProcessor', 'intermediate:InnermostNodeMarginCalculator'), 'phase:ORTHOGONAL': ('phase:BRANDES_KOEPF', 'intermediate:LayerSizeAndGraphHeightCalculator'), 'import:json-to-layered': ('direction:transpose', 'components:split', 'intermediate:LabelAndNodeSizeProcessor'), 'export:layered-to-json': ('components:layout-finalization', 'components:simple-row-combine', 'intermediate:LongEdgeJoiner', 'intermediate:SelfLoopPostProcessor', 'intermediate:ReversedEdgeRestorer'), 'pipeline:default-processor-configuration': ('import:json-to-layered', 'export:layered-to-json', 'direction:mirror-x', 'direction:mirror-y', 'direction:transpose', 'components:split', 'components:layout-finalization', 'components:simple-row-combine', 'phase:GREEDY', 'phase:NETWORK_SIMPLEX', 'phase:LAYER_SWEEP_BARYCENTER', 'phase:LAYER_SWEEP_GREEDY_SWITCH', 'phase:BRANDES_KOEPF', 'phase:ORTHOGONAL')}


EXPECTED_SUPPORT_SELECTORS = {'direction:mirror-x': [('references/e04-source-components-A.json', '/hostMappingProofs', None), ('references/e05-source-components-A.json', '/components/2', None), ('references/e06-component-approvals.json', '', None), ('references/e06-source-components-A.json', '', None), ('references/e06-source-components-A.json', '/components/3', None), ('references/e06-source-components-B.json', '', None), ('references/e06-source-components-R.json', '', None)], 'direction:mirror-y': [('references/e04-source-components-A.json', '/hostMappingProofs', None), ('references/e05-source-components-A.json', '/components/2', None), ('references/e06-component-approvals.json', '', None), ('references/e06-source-components-A.json', '', None), ('references/e06-source-components-A.json', '/components/3', None), ('references/e06-source-components-B.json', '', None), ('references/e06-source-components-R.json', '', None)], 'direction:transpose': [('references/e04-source-components-A.json', '/hostMappingProofs', None), ('references/e05-source-components-A.json', '/components/2', None), ('references/e06-component-approvals.json', '', None), ('references/e06-source-components-A.json', '', None), ('references/e06-source-components-A.json', '/components/3', None), ('references/e06-source-components-B.json', '', None), ('references/e06-source-components-R.json', '', None)], 'phase:NETWORK_SIMPLEX': [('references/e06-component-approvals.json', '', None), ('references/e06-source-components-A.json', '', None), ('references/e06-source-components-A.json', '/components/3', None), ('references/e06-source-components-B.json', '', None), ('references/e06-source-components-R.json', '', None)], 'components:split': [('references/e04-source-components-A.json', '/hostSupportPolicy', None)], 'components:simple-row-combine': [('references/e04-source-components-A.json', '/hostSupportPolicy', None), ('references/e06-source-components-A.json', '/components/5/hostMappings/1', '2737ac5280487fb8bb4a554edeadf9704b17ed5360ad38d506afdbea11c20fc7')], 'components:layout-finalization': [('references/e04-source-components-A.json', '/hostSupportPolicy', None)]}
B_REVIEWED_R_IDS = {'intermediate:ReversedEdgeRestorer', 'intermediate:SelfLoopRouter', 'intermediate:SelfLoopPreProcessor', 'intermediate:LongEdgeJoiner', 'intermediate:SelfLoopPostProcessor', 'intermediate:InLayerConstraintProcessor', 'intermediate:LongEdgeSplitter', 'intermediate:PortListSorter', 'intermediate:EndLabelSorter', 'intermediate:EdgeAndLayerConstraintEdgeReverser', 'intermediate:PortSideProcessor', 'intermediate:SelfLoopPortRestorer', 'intermediate:LayerConstraintPreprocessor', 'intermediate:LayerConstraintPostprocessor'}

def no_runtime_claims(value):
    base.no_runtime_claims(value)
    for _, item in walk(value):
        for key in {"wholeE07SourceGateApproved", "wholeE07SourceGateAccepted"} & item.keys():
            require(item[key] is False, "Source-only evidence promotes whole E07 gate")


source_context = base.source_context


def inherited_artifacts(component, root=ROOT):
    """Bind exact artifacts AND typed selectors, never only a rebound SHA."""
    records = {}
    for _, item in walk(component):
        path = item.get("path")
        if not isinstance(path, str) or not path.startswith(("references/", "src/")) or "sha256" not in item:
            continue
        expected = INHERITED.get(path, LICENSES.get(path))
        require(expected is not None and item["sha256"] == expected and sha256(contained(root, path)) == expected,
                "Fixed inherited source/license bytes differ: " + path)
        records[path] = expected
    if component["componentId"] in EXPECTED_SUPPORT_SELECTORS:
        selectors = sorted((item["artifact"]["path"], item.get("jsonPointer"), item.get("selectedSha256"))
                           for _, item in walk(component) if type(item.get("artifact")) is dict)
        require(selectors == EXPECTED_SUPPORT_SELECTORS[component["componentId"]],
                "Required inherited support selector/role denominator differs")
    for _, item in walk(component):
        artifact = item.get("artifact")
        if not isinstance(artifact, dict):
            continue
        require(artifact.get("path") in records, "Inherited artifact is outside fixed registry")
        old = load(contained(root, artifact["path"]))
        require("jsonPointer" in item, "Inherited artifact lacks explicit typed selector")
        target = json_pointer(old, item["jsonPointer"])
        if "selectedSha256" in item:
            require(canonical_sha(target) == item["selectedSha256"], "Inherited selected support proof seal differs")
        if "canonicalComponentSha256" in item:
            require(type(target) is dict and target.get("componentId") == component["componentId"] and
                    canonical_sha(target) == item["canonicalComponentSha256"], "Inherited component role/seal differs")
            proofs = target.get("guardProofs", target.get("sourceDerivation", []))
            require(type(proofs) is list and proofs and
                    item.get("requiredProofIds") == [p["id"] for p in proofs], "Complete inherited proof IDs are missing or differ")
    return [{"path": path, "sha256": records[path]} for path in sorted(records)]


def validate_document(document, lane, root=ROOT):
    require(document["schema"] == "py-elk-e07-component-sources/v1" and document["lane"] == lane,
            "E07 source schema/ownership differs")
    require(document["algorithmSourceGate"] in {"unverified", "unverified-for-E07-expansion"} and
            document["nativeLayoutImplemented"] is False, "Source proposal promotes runtime/gate")
    exact_zero(document["pythonAlgorithmsVerified"]); no_runtime_claims(document)
    sources = base.validate_sources(document, lane)
    common = document["commonSourceContext"]
    require(canonical_sha(common) == document["commonSourceContextSha256"] == COMMON_CONTEXT_SHA,
            "Common source guards/context differ")
    require(canonical_sha(document["sourceContext"]) == CONTEXT_SHA[lane], "Lane source context differs")
    if "sourceContextSha256" in document:
        require(document["sourceContextSha256"] == CONTEXT_SHA[lane], "Lane context seal differs")
    rows = document["components"]
    require(type(rows) is list and rows, "Vacuous component list")
    components = {c["componentId"]: c for c in rows}
    require(len(components) == len(rows) and set(components) <= FINAL_COMPONENT_IDS[lane], "Source component role denominator differs")
    seals = {}
    old_registry = {c["componentId"]: (l, i, c) for l, path in base.DOCUMENTS.items()
                    for i, c in enumerate(load(contained(root, path))["components"])}
    for identity, component in components.items():
        require(component["unresolved"] == [], "Component source closure is open")
        if lane == "A":
            require(component["actualPortSource"] == sources["elkjs-generated-worker"], "Actual source role differs")
            require(component["commonSourceContext"] == common and component["commonSourceContextSha256"] == COMMON_CONTEXT_SHA,
                    "Component common guards differ")
            expected = NS_CONTEXT_SHA if identity == "phase:NETWORK_SIMPLEX" else CONTEXT_SHA["A"]
            require(canonical_sha(component["sourceContext"]) == component["sourceContextSha256"] == expected,
                    "Component-specific source context differs")
            require(component["nativeExpansionImplemented"] is False and component["runtimeAcceptanceAssessed"] is False,
                    "A source promotes implementation")
            if identity.startswith("direction:"):
                require(tuple(p["id"] for p in component["sharedProofs"]) == SHARED_DIRECTION_PROOFS,
                        "Direction shared proof denominator differs")
                require(all(nonempty(p.get("proof", p.get("claim"))) for p in component["sharedProofs"]),
                        "Vacuous direction shared proof")
            else:
                require(any(link.get("artifact", {}).get("path") == base.DOCUMENTS["A"] and
                            link.get("jsonPointer") == "/components/3" for link in component["immutableSupportEvidence"]),
                        "NS omits complete inherited kernel role")
        elif lane == "B":
            require(component["role"] == identity and component["closureStatus"] == "closed-under-explicit-component-operation-guards" and
                    component["commonSourceContext"] == common and component["commonSourceContextSha256"] == COMMON_CONTEXT_SHA and
                    component["nativeRuntimeAccepted"] is False, "B component operation/context differs")
        else:
            require(component["role"] == "renewed-E06-fixed-source-component" and
                    component["closureStatus"] == "component-source-proposed" and component["nativeRuntimeAccepted"] is False,
                    "Renewed component role/closure differs")
            old_lane, old_index, original = old_registry[identity]
            inherited = component["inheritedComponent"]
            require(inherited["artifact"] == {"path": base.DOCUMENTS[old_lane], "sha256": INHERITED[base.DOCUMENTS[old_lane]]} and
                    inherited["jsonPointer"] == f"/components/{old_index}" and
                    inherited["canonicalComponentSha256"] == canonical_sha(original), "Wrong inherited E06 component role")
            require(component["notInheritedDomainAssumptions"] == ["RIGHT-only raw graph", "one weakly connected raw graph"],
                    "Renewal silently inherits excluded old outer guards")
        proofs = component["guardProofs"]
        require(type(proofs) is list and tuple(p["id"] for p in proofs) == REQUIRED_PROOF_IDS[identity],
                "Required component proof ID denominator differs: " + identity)
        for proof in proofs:
            meaning = proof.get("proof", proof.get("claim", proof.get("claims")))
            require(nonempty(meaning) or (type(meaning) is list and meaning and all(nonempty(x) for x in meaning)),
                    "Vacuous source derivation")
            if "sourceRefs" in proof:
                require(type(proof["sourceRefs"]) is list and proof["sourceRefs"], "Proof lacks actual bounded source anchors")
            else:
                symbols = {span["symbol"] for _, span in span_records(component)}
                require(type(proof.get("sourceSymbols")) is list and proof["sourceSymbols"] and
                        all(name in symbols for name in proof["sourceSymbols"]), "Proof cites unbound or empty source symbols")
        for key in ("reads", "writes"):
            require(type(component[key]) is list and (component[key] or lane == "R") and
                    all(nonempty(x) for x in component[key]), "Vacuous component read/write semantics")
        entry = component.get("entryAndAlgorithmHelpers", component.get("entrySpans"))
        require(type(entry) is list and entry, "Missing actual entry source")
        inherited_artifacts(component, root)
        seals[identity] = canonical_sha(component)
    require(document["componentSeals"] == seals, "Declared component seals differ")
    for _, span in span_records(document): validate_span_shape(span, sources)
    require(span_records(document), "No bounded source spans")
    for _, edge in edge_records(document):
        require(nonempty(edge["caller"]) and edge["callee"] == edge["calleeSpan"]["symbol"] and
                type(edge["callSiteLines"]) is list and edge["callSiteLines"] and
                all(type(n) is int and n > 0 for n in edge["callSiteLines"]), "Static call-site binding differs")
    return {"components": components, "seals": seals, "sources": sources}


def validate_dependencies(component, registry):
    identity = component["componentId"]; deps = component.get("componentDependencies", [])
    require(type(deps) is list and tuple(d["componentId"] for d in deps) == REQUIRED_DEPENDENCIES[identity],
            "Required typed source dependencies differ: " + identity)
    for dep in deps:
        target = registry.get(dep["componentId"])
        require(target is not None and dep.get("canonicalComponentSha256") == canonical_sha(target),
                "Typed dependency target/seal differs")
        require(nonempty(dep.get("meaning")), "Vacuous typed dependency meaning")


def review_binding(review, row, identity, registry):
    lane = row["lane"]
    require(review["status"] == "ACCEPTED_UNDER_COMPONENT_GUARDS" and
            review["sourceDocument"] == {"path": row["sourceDocument"], "sha256": row["sourceDocumentSha256AtReview"]},
            "Independent reviewed document/status differs")
    no_runtime_claims(review)
    require(review["commonSourceContextSha256"] == COMMON_CONTEXT_SHA, "Review common source context differs")
    if review["schema"] == "py-elk-e07-component-source-review/v1":
        expected_reviewer = "B" if identity in B_REVIEWED_R_IDS else "V"
        require(lane in {"A", "R"} and row["reviewerLane"] == review["reviewer"] == expected_reviewer and
                review["reviewedLane"] == lane and review["blockers"] == [] and
                review["nativeRuntimeAccepted"] is False and review["wholeE07SourceGateApproved"] is False,
                "Independent reviewer role/blockers differ")
        approved, seals = review["approvedComponents"], review["componentSeals"]
        require(type(approved) is list and approved and len(set(approved)) == len(approved) and
                set(approved) <= FINAL_COMPONENT_IDS[lane] and set(seals) == set(approved) and identity in approved,
                "Review component/seal set differs")
        require(review["sourceContextSha256"] == CONTEXT_SHA[lane], "Review lane context differs")
        require(all(("B" if item in B_REVIEWED_R_IDS else "V") == expected_reviewer for item in approved),
                "Review component set crosses fixed independent reviewer roles")
        for item in approved:
            require(item in registry and seals[item] == canonical_sha(registry[item]), "Reviewed component seal differs")
        require(set(review["componentDependencies"]) == set(approved), "Review typed-dependency denominator differs")
        deps = review["componentDependencies"][identity]
    else:
        require(review["schema"] == "py-elk-e07-independent-source-review/v1" and
                lane == "B" and review["ownerLane"] == lane and review["reviewerLane"] == row["reviewerLane"] == "A",
                "Independent A/B reviewer role differs")
        entries = review["components"]
        require(type(entries) is list and entries and len({x["componentId"] for x in entries}) == len(entries) and
                {x["componentId"] for x in entries} <= FINAL_COMPONENT_IDS[lane], "Review component denominator differs")
        for entry in entries:
            require(entry["status"] == "ACCEPTED_UNDER_COMPONENT_GUARDS" and entry["componentId"] in registry and
                    entry["canonicalComponentSha256"] == canonical_sha(registry[entry["componentId"]]), "Independent reviewed role/seal differs")
        selected = [e for e in entries if e["componentId"] == identity]
        require(len(selected) == 1 and all(x.get("status") == "resolved" for x in review.get("findings", [])),
                "Independent review omits component or has open findings")
        deps = selected[0].get("componentDependencies", [])
    require(deps == row["componentDependencies"] == registry[identity].get("componentDependencies", []),
            "Reviewed/approved typed dependency receipt differs")


def validate_approvals(manifest, documents, validated, root):
    require(manifest["schema"] == "py-elk-e07-component-approvals/v1" and manifest["iteration"] == "E07",
            "Approval schema/iteration differs")
    gate = manifest["globalAlgorithmSourceGate"]
    require(gate in {"verified", "unverified-for-E07-expansion"} and
            manifest["status"] == ("E07_SOURCE_SCOPE_VERIFIED" if gate == "verified" else "E07_SOURCE_SCOPE_PENDING"),
            "Whole gate/status differs")
    require(manifest["scopeDocument"] == SCOPE and manifest["scopeDocumentSha256"] == sha256(contained(root, SCOPE)), "Scope receipt differs")
    require(manifest["expectedComponentCounts"] == {lane: len(ids) for lane, ids in FINAL_COMPONENT_IDS.items()} and
            type(manifest["expectedComponentCount"]) is int and manifest["expectedComponentCount"] == 33,
            "Whole33 source denominator differs")
    require(manifest["componentEncoding"] == ENCODING and manifest["licenseSha256"] == LICENSES, "Encoding/license denominator differs")
    no_runtime_claims(manifest)
    for path, fingerprint in LICENSES.items(): require(sha256(contained(root, path)) == fingerprint, "Packaged source notice differs")
    rows = manifest["approvals"]
    require(type(rows) is list and len({r["componentId"] for r in rows}) == len(rows), "Duplicate approval")
    registry = {identity: c for v in validated.values() for identity, c in v["components"].items()}
    for row in rows:
        identity, lane = row["componentId"], row["lane"]
        require(lane in DOCUMENTS and identity in FINAL_COMPONENT_IDS[lane] and identity in registry and
                row["sourceDocument"] == DOCUMENTS[lane], "Approved ownership/source role differs")
        require(row["status"] == "verified-for-component-porting" and row["runtimeAccepted"] is False,
                "Source component approval promotes runtime")
        for key in ("sourceDocumentSha256AtReview", "sourceDocumentSha256AtApproval", "scopeDocumentSha256AtApproval",
                    "canonicalComponentSha256", "sourceContextSha256", "versionedReviewSha256"): digest(row[key])
        require(row["canonicalComponentSha256"] == canonical_sha(registry[identity]) and
                row["sourceContextSha256"] == canonical_sha(source_context(documents[lane])), "Approved component/context seal differs")
        require(row["inheritedArtifacts"] == inherited_artifacts(registry[identity], root), "Approved inherited closure differs")
        path = row["versionedReview"]
        require(type(path) is str and path.startswith("references/e07-reviews/") and
                sha256(contained(root, path)) == row["versionedReviewSha256"], "Independent raw review bytes differ")
        review_binding(load(contained(root, path)), row, identity, registry)
    for component in registry.values(): validate_dependencies(component, registry)
    if gate == "verified":
        require({r["componentId"] for r in rows} == set(registry) == ALL_COMPONENT_IDS, "Whole gate needs all33 exact source approvals")
        require(manifest["finalSourceDocumentsSha256"] == {p: sha256(contained(root, p)) for p in DOCUMENTS.values()},
                "Whole source final document bytes differ")
    return {"approvedComponents": len(rows), "componentIds": [r["componentId"] for r in rows], "wholeDenominatorFrozen": True}


def validate_symbol_bindings(document, blobs):
    """All NEW E07 spans use literal tokens/functions; no semantic exception."""
    texts = {k: v.decode("utf8") for k, v in blobs.items()}
    utf16 = {key: value.encode("utf-16-le") for key, value in texts.items()}
    rows = {key: value.splitlines() for key, value in texts.items()}
    for _, span in span_records(document):
        text = texts[span["sourceId"]]
        if "functionStartOffset" in span:
            body = utf16[span["sourceId"]][span["functionStartOffset"] * 2:span["functionEndOffset"] * 2].decode("utf-16-le")
            found = re.match(r"function\s+([\w$]+)\s*\(", body)
            require(found is not None and found[1] == span["symbol"], "Actual function symbol differs")
        else:
            excerpt = "\n".join(rows[span["sourceId"]][span["startLine"] - 1:span["endLine"]])
            require(re.search(r"(?<![\w$])" + re.escape(span["symbol"]) + r"(?![\w$])", excerpt), "Literal source token is absent")
    return {"literalSymbolCount": len(span_records(document)), "newSemanticLabelExceptions": 0}


def evidence_paths(root=ROOT):
    paths = base.evidence_paths(root) | {MANIFEST, SCOPE, *DOCUMENTS.values(), *INHERITED, *LICENSES}
    paths |= {row["versionedReview"] for row in load(contained(root, MANIFEST))["approvals"]}
    return paths


@readonly_source_check
def check(root=ROOT, *, with_upstream=False, require_approved=False):
    root = Path(root); errors, counts, missing, fingerprints = [], {}, {}, {}; approvals = canonical = None; whole = False
    try:
        fingerprints = {p: sha256(contained(root, p)) for p in evidence_paths(root)}
        old = base.check(root, require_approved=True)
        require(old["status"] == "E06_SOURCE_BINDINGS_VALIDATED" and old["wholeSourceApproved"],
                "Complete fixed E06 inheritance failed: " + "; ".join(old["errors"]))
        for path, fingerprint in INHERITED.items(): require(sha256(contained(root, path)) == fingerprint, "Inherited source identity differs")
        documents = {lane: load(contained(root, path)) for lane, path in DOCUMENTS.items()}
        validated = {lane: validate_document(document, lane, root) for lane, document in documents.items()}
        counts = {lane: len(v["components"]) for lane, v in validated.items()}
        missing = {lane: sorted(ids - set(validated[lane]["components"])) for lane, ids in FINAL_COMPONENT_IDS.items()}
        manifest = load(contained(root, MANIFEST)); approvals = validate_approvals(manifest, documents, validated, root)
        whole = manifest["globalAlgorithmSourceGate"] == "verified" and not any(missing.values())
        if require_approved: require(whole, "Whole E07 source gate remains pending; all33 required")
        if with_upstream:
            import upstream
            lock = load(root / "UPSTREAM.json"); upstream.verify_source(root / ".local/upstream-elkjs", lock)
            upstream.verify_package(root / ".local/npm-elkjs/package", lock); canonical = {}
            for lane, document in documents.items():
                blobs = {s["sourceId"]: upstream.git(root / ".local/upstream-elkjs", "show", s["commit"] + ":" + s["path"]) for s in document["sources"]}
                for source in document["sources"]:
                    require(upstream.git(root / ".local/upstream-elkjs", "rev-parse", source["commit"] + ":" + source["path"]).decode().strip() == source["gitBlob"],
                            "Actual Git blob differs")
                canonical[lane] = validate_canonical(document, blobs); validate_function_line_alignment(document, blobs)
                canonical[lane].update(validate_symbol_bindings(document, blobs))
        require(all(sha256(contained(root, p)) == h for p, h in fingerprints.items()), "Evidence changed during validation; rerun after stability")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e07-source-validation/v1", "status": "FAIL" if errors else "E07_SOURCE_BINDINGS_VALIDATED" if whole else "E07_SOURCE_BINDINGS_PARTIAL",
            "errors": errors, "componentCounts": counts, "expectedComponentCounts": {lane: len(ids) for lane, ids in FINAL_COMPONENT_IDS.items()},
            "fullDenominatorFrozen": True, "missingProposedComponentIds": missing, "approvedEvidence": approvals,
            "wholeSourceApproved": whole and not errors, "canonicalVerified": bool(with_upstream and not errors), "canonical": canonical,
            "inputSha256": fingerprints, "validatorSha256": sha256(Path(__file__)), "runtimeAcceptanceAssessed": False,
            "mathematicalEquivalenceAutomaticallyProved": False, "pythonAlgorithmsVerified": 0,
            "limitation": "Versioned source/proof identities and independent reviews only. Full E06 inheritance is exact; no new semantic-label exceptions. Canonical source checks need --with-upstream. Runtime/math equivalence/release are separate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true"); parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(); result = check(with_upstream=args.with_upstream, require_approved=args.require_approved)
    if args.out: write(args.out, result)
    print(json.dumps(result, indent=2)); return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
