"""Validate E06 source receipts, never approve components or execute layout.

Offline checks require only versioned evidence. --with-upstream additionally
rechecks canonical Git/npm bytes, LF spans, UTF16 functions and lexical calls.
Neither mode automatically proves the mathematical derivations or runtime.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from layout_checks import ROOT, contained, load, sha256, write
from source_read_cache import readonly_source_check
from validate_e04_source_bindings import edge_records, span_records, validate_canonical, validate_span_shape, walk
import validate_e05_source_bindings as base
from validate_e05_source_bindings import (BASELINE, ENCODING, SOURCE_IDENTITIES, canonical_sha,
                                         digest, exact_zero, json_pointer, nonempty, require,
                                         validate_function_line_alignment)

DOCUMENTS = {lane: f"references/e06-source-components-{lane}.json" for lane in "ABR"}
MANIFEST = "references/e06-component-approvals.json"
SCOPE = "docs/decisions/0005-e06-multigraph.md"
UNMERGED = "references/e06-default-unmerged.json"
FINAL_COMPONENT_IDS = {
    "A": {"graph:edge-reversal", "phase:GREEDY", "phase:NETWORK_SIMPLEX", "import:json-to-layered", "export:layered-to-json"} |
         {"intermediate:" + name for name in ("ReversedEdgeRestorer", "LongEdgeSplitter", "LongEdgeJoiner")},
    "B": {"intermediate:SelfLoop" + name for name in ("PreProcessor", "PortRestorer", "Router", "PostProcessor")},
    "R": {"pipeline:default-processor-configuration", "phase:LAYER_SWEEP_BARYCENTER", "phase:LAYER_SWEEP_GREEDY_SWITCH",
          "phase:BRANDES_KOEPF", "phase:ORTHOGONAL"} |
         {"intermediate:" + name for name in (
             "EdgeAndLayerConstraintEdgeReverser", "LayerConstraintPreprocessor", "LayerConstraintPostprocessor",
             "PortSideProcessor", "PortListSorter", "InLayerConstraintProcessor", "LabelAndNodeSizeProcessor",
             "InnermostNodeMarginCalculator", "LayerSizeAndGraphHeightCalculator", "EndLabelSorter")},
}
ALL_COMPONENT_IDS = set().union(*FINAL_COMPONENT_IDS.values())
LICENSES = {**base.LICENSES, "src/pyelk/_licenses/NOTICE-E06.md":
            "9635aa08b74e73edb2a6ce80c90a1be05185b598426981cc924d2b195ac57858"}
INHERITED = {
    **base.INHERITED,
    "references/e05-source-components-A.json": "b78adcc0ed6b665a1f1cde35d53b03ed8e9adfbf611e45e508619101754e8ec0",
    "references/e05-source-components-B.json": "098e9069099b8a45af61d5225c0a2f93ff27fefe868d62eea017c3ee3eae378b",
    "references/e05-source-routing.json": "72e61a4919aa174885cf4e9f6909c5827f50b7df93c78d2af371cc629cfaed7e",
    "references/layered-default-path.json": "245e791b04ef74962ef79c18b1d2bea1afd74d70a95dc95b4100d4761563608f",
    UNMERGED: "55ab82b2158c84c7e0d5d651a58db841ac40accda6f7e8edfc0765c40498b5b2",
    "references/licenses/elkjs-LICENSE.md": SOURCE_IDENTITIES["elkjs-license"][2],
}
# These shared contexts were reviewed separately from component bodies. Their
# immutable hashes prevent changing guards while keeping a component seal.
CONTEXT_SHA = {"A": "e9054c6ddfb15478df5676340a0237691b73daa450e564227b7147a67aa46a73",
               "B": "ddd648721a45968e7a343181e91d77e504959ec2196ec10230a6ce508e3418e4",
               "R": "8e8a7e51b814ac6b6f5364f4bcce3b9cc174066d286e56e48cb1830eaebf7a4b"}
REQUIRED_DEPENDENCIES = {
    "phase:GREEDY": {"graph:edge-reversal"},
    "intermediate:ReversedEdgeRestorer": {"graph:edge-reversal"},
    "phase:NETWORK_SIMPLEX": {"phase:GREEDY"},
    "intermediate:LongEdgeSplitter": {"phase:NETWORK_SIMPLEX", "graph:edge-reversal"},
    "intermediate:LongEdgeJoiner": {"intermediate:LongEdgeSplitter", "intermediate:ReversedEdgeRestorer"},
    "export:layered-to-json": {"intermediate:LongEdgeJoiner", "intermediate:SelfLoopPostProcessor", "intermediate:ReversedEdgeRestorer"},
    "intermediate:SelfLoopRouter": {"intermediate:SelfLoopPreProcessor", "intermediate:SelfLoopPortRestorer"},
    "phase:LAYER_SWEEP_BARYCENTER": {"phase:NETWORK_SIMPLEX", "intermediate:LongEdgeSplitter",
                                    "intermediate:SelfLoopPreProcessor", "intermediate:PortSideProcessor", "intermediate:PortListSorter"},
    "phase:LAYER_SWEEP_GREEDY_SWITCH": {"phase:LAYER_SWEEP_BARYCENTER"},
    "phase:BRANDES_KOEPF": {"phase:LAYER_SWEEP_GREEDY_SWITCH", "intermediate:SelfLoopPortRestorer",
                            "intermediate:LabelAndNodeSizeProcessor", "intermediate:InnermostNodeMarginCalculator", "intermediate:SelfLoopRouter"},
    "phase:ORTHOGONAL": {"phase:BRANDES_KOEPF", "intermediate:LayerSizeAndGraphHeightCalculator"},
    "pipeline:default-processor-configuration": {"import:json-to-layered", "phase:GREEDY", "phase:NETWORK_SIMPLEX",
        "phase:LAYER_SWEEP_BARYCENTER", "phase:LAYER_SWEEP_GREEDY_SWITCH", "phase:BRANDES_KOEPF", "phase:ORTHOGONAL"} | FINAL_COMPONENT_IDS["B"],
}
REQUIRED_PROOF_IDS = {
    ("phase:NETWORK_SIMPLEX", "phase:GREEDY"): ["GR-G4-REVERSAL-AND-CYCLIC", "GR-G6-SIMPLE-RING"],
    ("intermediate:LongEdgeSplitter", "phase:NETWORK_SIMPLEX"): ["NS-G4-NORMALIZE-BALANCE", "NS-G6-SPLIT-SCALE"],
}
# These exact, independently reviewed A labels describe bounded source ranges;
# they are NOT generated function names or literal callees. Pin all 13 JSON
# locations as well as the worker identity, LF range, label, SHA and actual role.
_LABELS = {
    "reversed": ("REVERSED scalarfalse default", 48652, 48652, "4f26bd057368f7996e030296700ba112dd067b8aa5ec93750bd1df5dfc8c47e6", "scalar-property-default-range", None),
    "collector": ("Collector flags and CYCLIC scalarfalse defaults", 48676, 48678, "237de1ba8dbc4578d2549c2a1e91c0f3554251a64abfe164c74bcc9553b33ccf", "scalar-property-default-range", None),
    "queues": ("Greedy per-call source/sink lists", 50521, 50525, "96d04e73c06295fc0ead8d8dac70c93f5ab1e953c0a6310d43b306a5331fc66f", "per-instance-constructor-state-range", None),
    "getter": ("Property.getDefault", 69799, 69811, "2ecc6351e7c9c8fa9f64f61b1c0de5e5fad9fe0933063b8f0dbc81698d0ff5a6", "property-default-getter-namespace-alias", "getDefault"),
    "interface": ("KVectorChain implements Cloneable4", 70595, 70595, "e6d53001ea46483497273b469ef2b67b345b57a7c6288d95a956e768c3316026", "generated-type-interface-registration-range", None),
    "registry": ("LayoutMetaDataService vector clone registration", 69351, 69353, "db9ae21e9039899b9d83ef29002fef33265c88fb3117b9522176e616e2c90d32", "mutable-default-clone-registration-range", None),
    "dispatch": ("LayoutMetaDataService lambda3 clone dispatch", 69581, 69585, "eef607a4a49c8ff84d37e7b9cc898ce00b759dd1fa70fb32547af853f20e5aa8", "generated-clone-prototype-dispatch-range", None),
    "constraints": ("Original constraints and loop holder defaults", 48688, 48689, "7e48f37a52c0eaa7e2ccdb2cc505ec199cb7d8b5ac2ce8a6e104cbdb364dff1b", "private-property-declaration-range", None),
    "combine": ("Single component combine_1", 31183, 31201, "411d057070ce0f105e8d590dd1977ef6cfe157e23b1e93bc9b5d650a33261e58", "single-component-combine-branch-range", None),
}
SEMANTIC_LABELS = {
    "/components/0/guardProofs/1/sourceRefs/2": _LABELS["reversed"],
    "/components/0/guardProofs/1/sourceRefs/3": _LABELS["collector"],
    "/components/1/supportDefaultSpans/2": _LABELS["queues"],
    "/components/6/supportDefaultSpans/0": _LABELS["constraints"],
    "/components/7/guardProofs/0/sourceRefs/2": _LABELS["combine"],
    **{f"/components/{index}/hostMappings/1/sourceSpans/{offset}": _LABELS[key]
       for index in (4, 5) for offset, key in ((10, "getter"), (11, "interface"), (12, "registry"), (13, "dispatch"))},
}


def no_runtime_claims(value):
    base.no_runtime_claims(value)
    for _, item in walk(value):
        for key in {"runtimeVerified", "wholeE06SourceGateApproved", "wholeE06SourceGateAccepted"} & item.keys():
            require(item[key] is False, "Source-only evidence promotes runtime/whole gate: " + key)


def source_context(document):
    return {"baseline": document["baseline"],
            "sources": [{k: v for k, v in row.items() if k != "localPath"} for row in document["sources"]],
            "commonSourceContext": document.get("commonSourceContext"), "sourceContext": document.get("sourceContext")}


def inherited_artifacts(component, root=ROOT):
    """Exact root approval protocol: all nested references/src SHA receipts."""
    records = {}
    for _, item in walk(component):
        path = item.get("path")
        if not isinstance(path, str) or not path.startswith(("references/", "src/")) or "sha256" not in item:
            continue
        require(path in INHERITED or path in LICENSES, "Unregistered inherited source/proof artifact: " + path)
        expected = INHERITED.get(path, LICENSES.get(path))
        require(item["sha256"] == expected and sha256(contained(root, path)) == expected, "Inherited shared proof bytes differ: " + path)
        records[path] = expected
    for _, item in walk(component):
        artifact = item.get("artifact", item.get("immutableSupportEvidence"))
        if not isinstance(artifact, dict):
            continue
        require(artifact.get("path") in records, "Inherited artifact is outside fixed source registry")
        inherited = load(contained(root, artifact["path"]))
        if "jsonPointer" in item:
            target = json_pointer(inherited, item["jsonPointer"])
            if "componentId" in item:
                require(type(target) is dict and target.get("componentId") == item["componentId"], "Inherited component pointer resolves to another component")
                if "canonicalComponentSha256" in item:
                    require(canonical_sha(target) == item["canonicalComponentSha256"], "Inherited component proof seal differs")
        elif "componentId" in item:
            targets = [c for c in inherited.get("components", []) if c["componentId"] == item["componentId"]]
            require(len(targets) == 1, "Inherited component reference does not resolve uniquely")
        if "componentId" in item and "canonicalComponentSha256" in item:
            matches = [c for c in inherited.get("components", []) if c["componentId"] == item["componentId"]]
            require(len(matches) == 1 and canonical_sha(matches[0]) == item["canonicalComponentSha256"], "Inherited component seal differs")
    return [{"path": path, "sha256": records[path]} for path in sorted(records)]


def validate_inherited_role(component, lane, root):
    identity = component["componentId"]
    if lane == "R":
        links = component["inheritedSourceBindings"]
        require(type(links) is list and len(links) == 1, "R inherited source role denominator differs")
        if identity == "pipeline:default-processor-configuration":
            require(links[0].get("artifact") == {"path": "references/layered-default-path.json", "sha256": INHERITED["references/layered-default-path.json"]}, "Pipeline omits its fixed default-order source inheritance")
        else:
            expected_path = (base.DOCUMENTS["B"] if identity in {"phase:LAYER_SWEEP_BARYCENTER", "phase:LAYER_SWEEP_GREEDY_SWITCH", "phase:BRANDES_KOEPF"}
                             else base.DOCUMENTS["R"] if identity == "phase:ORTHOGONAL" else base.DOCUMENTS["A"])
            require(links[0].get("artifact") == {"path": expected_path, "sha256": INHERITED[expected_path]} and links[0].get("componentId") == identity,
                    "Inherited source role belongs to a different component")
    if lane == "A" and identity in {"import:json-to-layered", "export:layered-to-json"}:
        link = component["inheritedSourceBindings"]
        require(type(link) is dict and link["artifact"]["path"] == "references/e04-source-components-A.json" and
                json_pointer(load(root / link["artifact"]["path"]), link["jsonPointer"])["componentId"] == identity,
                "Inherited transfer source role differs")
    if identity == "import:json-to-layered":
        links = component.get("immutableDefaultUnmerged")
        require(type(links) is list and len(links) == 1 and links[0].get("artifact") == {"path": UNMERGED, "sha256": INHERITED[UNMERGED]} and
                links[0].get("jsonPointer") == "/claims", "Importer omits its exact default-unmerged proof closure")


def validate_sources(document, lane):
    require(document["baseline"] == BASELINE and all(type(document["baseline"][k]) is str for k in BASELINE), "Fixed source baseline differs")
    expected = {"elkjs-generated-worker", "elkjs-license"} | ({"elkjs-package"} if lane in {"A", "R"} else set())
    rows = document["sources"]
    require(type(rows) is list and len(rows) == len(expected), "Fixed source denominator differs")
    by_source = {row["sourceId"]: row for row in rows}
    require(len(by_source) == len(rows) and set(by_source) == expected, "Fixed source roles differ")
    for identity, row in by_source.items():
        role_key = "kind" if lane in {"A", "R"} else "role"
        keys = {"sourceId", "path", "commit", "gitBlob", "sha256", role_key}
        require(keys <= row.keys() and set(row) <= keys | {"localPath"}, "Canonical source receipt fields differ")
        path, blob, fingerprint = SOURCE_IDENTITIES[identity]
        require((row["path"], row["gitBlob"], row["sha256"], row["commit"]) == (path, blob, fingerprint, BASELINE["commit"]), "Canonical source identity differs")
        expected_role = ("canonical-generated-artifact" if identity == "elkjs-generated-worker" else "fixed-elkjs-source") if lane in {"A", "R"} else (
            "direct-generated-algorithm-source" if identity == "elkjs-generated-worker" else "upstream-original-license" if identity == "elkjs-license" else "fixed-elkjs-package-metadata")
        require(row[role_key] == expected_role, "Canonical source role differs: " + identity)
    return by_source


def semantic_label_record(document, path, span):
    """Recognize only the fixed reviewed range descriptions, never a callee."""
    if document.get("lane") != "A" or path not in SEMANTIC_LABELS:
        return None
    label, start, end, fingerprint, role, function_alias = SEMANTIC_LABELS[path]
    source = next(s for s in document["sources"] if s["sourceId"] == span["sourceId"])
    require(source["sourceId"] == "elkjs-generated-worker" and source["path"] == "lib/elk-worker.js" and
            source["sha256"] == BASELINE["workerSha256"] and source["commit"] == BASELINE["commit"] and
            source["kind"] == "canonical-generated-artifact", "Semantic label belongs to another source identity/role")
    require((span["symbol"], span["startLine"], span["endLine"], span["spanSha256"]) == (label, start, end, fingerprint),
            "Reviewed semantic range label/location changed")
    require(("functionStartOffset" in span) == (function_alias is not None), "Semantic range/function alias role changed")
    return {"documentPointer": path, "sourcePath": source["path"], "sourceSha256": source["sha256"],
            "startLine": start, "endLine": end, "label": label, "role": role,
            "literalCallee": False, "actualFunctionAlias": function_alias}


def validate_symbol_bindings(document, raw_sources):
    """Additional E06 check: actual function names/tokens, with fixed labels."""
    sources = {key: raw.decode("utf-8") for key, raw in raw_sources.items()}
    utf16_sources = {key: value.encode("utf-16-le") for key, value in sources.items()}
    rows = {key: value.splitlines() for key, value in sources.items()}
    semantic, literals, aliases = [], 0, 0
    for path, span in span_records(document):
        label = semantic_label_record(document, path, span)
        text = sources[span["sourceId"]]
        if label is not None:
            semantic.append(label)
            if label["actualFunctionAlias"] is None:
                continue
            expected_name = label["actualFunctionAlias"]
            aliases += 1
        else:
            expected_name = span["symbol"]
            literals += 1
        if "functionStartOffset" in span:
            utf16 = utf16_sources[span["sourceId"]]
            body = utf16[span["functionStartOffset"] * 2:span["functionEndOffset"] * 2].decode("utf-16-le")
            found = re.match(r"function\s+([\w$]+)\s*\(", body)
            require(found is not None and found[1] == expected_name, "Exact function symbol differs from its canonical body")
        else:
            excerpt = "\n".join(rows[span["sourceId"]][span["startLine"] - 1:span["endLine"]])
            require(re.search(r"(?<![\w$])" + re.escape(expected_name) + r"(?![\w$])", excerpt), "Literal source symbol token is absent from its LF span")
    return {"semanticLabelCount": len(semantic), "literalSymbolCount": literals,
            "functionAliasCount": aliases, "semanticLabelBindings": semantic,
            "classification": "Reviewed range descriptions and one fixed namespace alias are explicitly separate from literal callee/function identities"}


def validate_document(document, lane, root=ROOT):
    require(document["schema"] == "py-elk-e06-component-sources/v1" and document["lane"] == lane, "E06 source schema/lane differs")
    require(document["algorithmSourceGate"] in {"unverified", "unverified-for-E06-expansion"}, "Source proposal cannot approve whole gate")
    require(document["nativeLayoutImplemented"] is False, "Source document claims native runtime")
    exact_zero(document["pythonAlgorithmsVerified"]); no_runtime_claims(document)
    sources = validate_sources(document, lane)
    context = document.get("sourceContext") if lane == "B" else document.get("commonSourceContext")
    require(type(context) is dict and canonical_sha(context) == CONTEXT_SHA[lane], "Shared context/proof guards differ")
    if lane != "B":
        require(document["commonSourceContextSha256"] == CONTEXT_SHA[lane], "Shared context seal differs")
    rows = document["components"]
    require(type(rows) is list and rows, "No component source proposal")
    components = {c["componentId"]: c for c in rows}
    require(len(components) == len(rows) and set(components) <= FINAL_COMPONENT_IDS[lane], "Fixed component denominator/ownership differs")
    seals = {}
    for identity, component in components.items():
        require(component["unresolved"] == [], "Component source closure is open")
        if lane == "A":
            require(component["status"] in {"ready-for-independent-source-review", "ready-for-independent-E06-source-review"}, "A component is not source-ready")
            require(component["actualPortSource"] == sources["elkjs-generated-worker"], "Component and shared source registry differ")
            require(component["commonSourceContext"] == context and component["commonSourceContextSha256"] == CONTEXT_SHA[lane], "Component context differs")
        elif lane == "B":
            require(component["closureStatus"] == "proposed-closed-under-explicit-default-implicit-port-guards", "B source closure differs")
        else:
            require(component["closureStatus"] == "ready-for-independent-source-review", "R source closure differs")
            require(component["sourceContext"] == context, "R component context differs")
        # R inherits actual read/write/helper semantics by exact E05 component
        # pointer/seal; it deliberately does not duplicate those array fields.
        for key in ("reads", "writes"):
            if lane != "R" or key in component:
                require(type(component[key]) is list and component[key] and all(nonempty(x) for x in component[key]), "Vacuous component " + key)
        if lane == "R":
            require(type(component["inheritedSourceBindings"]) is list and component["inheritedSourceBindings"], "Missing inherited actual source behavior")
        validate_inherited_role(component, lane, root)
        entry = component.get("entryAndAlgorithmHelpers", component.get("entrySpans"))
        require(type(entry) is list and entry, "Missing actual component entry")
        proofs = component.get("sourceDerivation", component.get("guardProofs"))
        require(type(proofs) is list and proofs and len({p["id"] for p in proofs}) == len(proofs), "Vacuous/duplicate component proof registry")
        symbols = {span["symbol"] for _, span in span_records(component)}
        proof_ids = {p["id"] for p in proofs} | {p["id"] for p in component.get("hostMappings", [])}
        for proof in proofs:
            require(nonempty(proof["id"]) and nonempty(proof.get("proof", proof.get("claim"))), "Vacuous guard proof")
            require("sourceRefs" in proof or "sourceSymbols" in proof or (identity, proof["id"]) in {
                ("import:json-to-layered", "IMP-G3-CARDINALITY"),
                ("export:layered-to-json", "EXP-G4-MODEL-DENOMINATOR")}, "Unregistered narrative proof lacks bounded anchors")
            if "sourceSymbols" in proof:
                require(type(proof["sourceSymbols"]) is list and proof["sourceSymbols"] and all(s in symbols for s in proof["sourceSymbols"]), "Guard proof cites unbound source symbol")
            if "sourceRefs" in proof:
                require(type(proof["sourceRefs"]) is list and proof["sourceRefs"], "Vacuous source proof anchors")
        for _, item in walk(component):
            if "proofRef" in item:
                require(item["proofRef"] in proof_ids, "Unknown source proofRef")
        notices = component["licenseRefs"]
        require(type(notices) is list and notices, "Missing actual component license")
        if all(type(item) is str for item in notices):
            require(lane == "B" and notices == ["elkjs-license"], "License source role differs")
        else:
            require(all(type(item) is dict and item.get("path") in LICENSES and item.get("sha256") == LICENSES[item["path"]] for item in notices), "License bytes/role differs")
            require({x["path"] for x in notices} >= {"src/pyelk/_licenses/elkjs-LICENSE.md", "src/pyelk/_licenses/NOTICE.md"}, "Missing source notices")
        inherited_artifacts(component, root)
        seals[identity] = canonical_sha(component)
    if "componentSeals" in document:
        require(document["componentSeals"] == seals, "Declared component seals differ")
    for _, span in span_records(document):
        validate_span_shape(span, sources)
    if lane == "A":
        labels = [semantic_label_record(document, path, span) for path, span in span_records(document)]
        if set(components) == FINAL_COMPONENT_IDS["A"]:
            require(sum(label is not None for label in labels) == 13, "Reviewed semantic range description denominator differs")
    require(span_records(document), "No bounded source spans")
    for _, edge in edge_records(document):
        require(nonempty(edge["caller"]) and nonempty(edge["callee"]) and edge["callee"] == edge["calleeSpan"]["symbol"] and
                type(edge["callSiteLines"]) is list and edge["callSiteLines"] and all(type(n) is int and n > 0 for n in edge["callSiteLines"]), "Static callsite binding differs")
    return {"components": components, "seals": seals, "sources": sources}


def validate_dependencies(component, registry):
    identity = component["componentId"]
    deps = component.get("componentDependencies", [])
    require(type(deps) is list and len({d["componentId"] for d in deps}) == len(deps), "Duplicate/invalid component dependency")
    require({d["componentId"] for d in deps} == REQUIRED_DEPENDENCIES.get(identity, set()), "Required source component dependency differs: " + identity)
    for dep in deps:
        target = registry.get(dep["componentId"])
        require(target is not None, "Source component dependency does not resolve")
        if "canonicalComponentSha256" in dep:
            require(dep["canonicalComponentSha256"] == canonical_sha(target), "Source component dependency seal differs")
        else:
            require(identity == "intermediate:SelfLoopRouter" and nonempty(dep.get("reason")), "Unsealed source dependency is not an explicit loop prerequisite")
        if "proofIds" in dep:
            ids = {p["id"] for key in ("guardProofs", "sourceDerivation") for p in target.get(key, [])}
            require(type(dep["proofIds"]) is list and dep["proofIds"] and len(dep["proofIds"]) == len(set(dep["proofIds"])) and all(p in ids for p in dep["proofIds"]), "Dependency proof IDs do not resolve")
        required_proofs = REQUIRED_PROOF_IDS.get((identity, dep["componentId"]))
        if required_proofs is not None:
            require(dep.get("proofIds") == required_proofs, "Required source dependency proof IDs are missing or differ")


def review_binding(review, row, identity):
    """Explicitly adapt the two independently produced E06 review schemas."""
    require(review["status"] == "ACCEPTED_UNDER_COMPONENT_GUARDS", "Independent review is not accepted")
    require(review["sourceDocument"] == {"path": row["sourceDocument"], "sha256": row["sourceDocumentSha256AtReview"]}, "Independent reviewed document receipt differs")
    no_runtime_claims(review)
    if review["schema"] == "py-elk-e06-component-source-review/v1":
        require(row["lane"] in {"A", "R"} and row["reviewerLane"] == "V" and review["reviewer"] == "V" and review["reviewedLane"] == row["lane"] and review["blockers"] == [], "V review identity/blockers differ")
        require(review["nativeRuntimeAccepted"] is False and review["wholeE06SourceGateApproved"] is False, "Source review promotes runtime/whole gate")
        approved, seals = review["approvedComponents"], review["componentSeals"]
        require(review["commonSourceContextSha256"] == CONTEXT_SHA[row["lane"]], "Independent review context seal differs")
        require(type(approved) is list and len(approved) == len(set(approved)) and set(approved) <= FINAL_COMPONENT_IDS[row["lane"]] and set(seals) == set(approved) and identity in approved and seals[identity] == row["canonicalComponentSha256"], "Independent reviewed component/seal differs")
        dependencies = review.get("componentDependencies", {}).get(identity, [])
    else:
        require(review["schema"] == "py-elk-e06-independent-source-review/v1" and review["reviewerLane"] == row["reviewerLane"] == ("A" if row["lane"] == "B" else "B") and review["ownerLane"] == row["lane"], "A/B independent reviewer identity differs")
        components = review["components"]
        require(type(components) is list and len({c["componentId"] for c in components}) == len(components) and
                {c["componentId"] for c in components} <= FINAL_COMPONENT_IDS[row["lane"]], "Independent review denominator/ownership differs")
        matches = [c for c in components if c["componentId"] == identity]
        require(len(matches) == 1 and matches[0]["status"] == "ACCEPTED_UNDER_COMPONENT_GUARDS" and matches[0]["canonicalComponentSha256"] == row["canonicalComponentSha256"], "Independent review component seal/status differs")
        require(all(f.get("status") == "resolved" for f in review.get("findings", [])), "Independent review has unresolved findings")
        dependencies = matches[0].get("componentDependencies", [])
    require(type(dependencies) is list and dependencies == row["componentDependencies"], "Reviewed typed component dependency receipt differs")
    return dependencies


def versioned_review_paths(manifest):
    return {row["versionedReview"] for row in manifest["approvals"]}


def validate_approvals(manifest, documents, validated, root):
    require(manifest["schema"] == "py-elk-e06-component-approvals/v1" and manifest["iteration"] == "E06", "E06 approval schema differs")
    gate = manifest["globalAlgorithmSourceGate"]
    require(gate in {"verified", "unverified-for-E06-expansion"} and manifest["status"] == ("E06_SOURCE_SCOPE_VERIFIED" if gate == "verified" else "E06_SOURCE_SCOPE_PENDING"), "Unknown or inconsistent whole source gate")
    require(manifest["scopeDocument"] == SCOPE and manifest["scopeDocumentSha256"] == sha256(contained(root, SCOPE)), "Current scope binding differs")
    require(manifest["componentEncoding"] == ENCODING and manifest["licenseSha256"] == LICENSES, "Component encoding/license denominator differs")
    for path, fingerprint in LICENSES.items():
        require(sha256(contained(root, path)) == fingerprint, "Packaged source license bytes differ")
    no_runtime_claims(manifest)
    rows = manifest["approvals"]
    require(type(rows) is list and len({r["componentId"] for r in rows}) == len(rows), "Approval denominator duplicate")
    approvals = {row["componentId"]: row for row in rows}
    registry = {identity: c for v in validated.values() for identity, c in v["components"].items()}
    for row in rows:
        identity, lane = row["componentId"], row["lane"]
        require(lane in DOCUMENTS and identity in FINAL_COMPONENT_IDS[lane] and identity in registry and row["sourceDocument"] == DOCUMENTS[lane], "Approval source/component ownership differs")
        require(row["status"] == "verified-for-component-porting" and row["runtimeAccepted"] is False, "Component source approval promotes runtime")
        require(not row.get("approvalHistory") and not row.get("sourceContextHistory"), "New source amendment needs an explicit reviewed protocol")
        for key in ("sourceDocumentSha256AtReview", "sourceDocumentSha256AtApproval", "scopeDocumentSha256AtApproval", "canonicalComponentSha256", "sourceContextSha256", "versionedReviewSha256"):
            digest(row[key])
        require(row["canonicalComponentSha256"] == validated[lane]["seals"][identity], "Approved component seal differs")
        require(row["sourceContextSha256"] == canonical_sha(source_context(documents[lane])), "Shared context changed outside approved component seal")
        require(row["inheritedArtifacts"] == inherited_artifacts(registry[identity], root), "Inherited proof closure receipt differs")
        path = row["versionedReview"]
        require(type(path) is str and path.startswith("references/e06-reviews/") and sha256(contained(root, path)) == row["versionedReviewSha256"], "Versioned independent review bytes differ")
        review_binding(load(root / path), row, identity)
        expected = registry[identity].get("componentDependencies", []) if lane != "B" else []
        require(row["componentDependencies"] == expected, "Approved dependency differs from source component closure")
    for component in registry.values():
        validate_dependencies(component, registry)
    whole = gate == "verified"
    if whole:
        require(set(approvals) == ALL_COMPONENT_IDS and set(registry) == ALL_COMPONENT_IDS, "Whole source gate must cover fixed27 component denominator")
        require(manifest.get("finalSourceDocumentsSha256") == {path: sha256(root / path) for path in DOCUMENTS.values()}, "Whole-source final document bytes differ")
    return {"approvedComponents": len(rows), "componentIds": list(approvals), "wholeDenominatorFrozen": True}


def evidence_paths(root=ROOT):
    """Versioned-only dependencies for reproducible offline test fixtures."""
    root = Path(root)
    paths = {MANIFEST, SCOPE, UNMERGED, *DOCUMENTS.values(), *INHERITED, *LICENSES,
             base.MANIFEST, base.SCOPE, *base.DOCUMENTS.values(), *base.INHERITED, *base.LICENSES, *base.AUXILIARY}
    for manifest_path in (MANIFEST, base.MANIFEST):
        manifest = load(root / manifest_path)
        paths |= versioned_review_paths(manifest) if manifest_path == MANIFEST else base.versioned_review_paths(manifest)
    return {path for path in paths if (root / path).is_file()}


@readonly_source_check
def check(root=ROOT, *, with_upstream=False, require_approved=False):
    root = Path(root)
    errors, counts, approvals, canonical, fingerprints, missing = [], {}, None, None, {}, {}
    whole = False
    try:
        paths = evidence_paths(root)
        fingerprints = {path: sha256(contained(root, path)) for path in paths}
        inherited = base.check(root, require_approved=True)
        require(inherited["status"] == "E05_SOURCE_BINDINGS_VALIDATED" and inherited["wholeSourceApproved"], "Full E05 source/review inheritance failed: " + "; ".join(inherited["errors"]))
        for path, fingerprint in INHERITED.items():
            require(sha256(contained(root, path)) == fingerprint, "Fixed inherited source/proof bytes differ")
        documents = {lane: load(root / path) for lane, path in DOCUMENTS.items()}
        validated = {lane: validate_document(doc, lane, root) for lane, doc in documents.items()}
        counts = {lane: len(v["components"]) for lane, v in validated.items()}
        missing = {lane: sorted(ids - set(validated[lane]["components"])) for lane, ids in FINAL_COMPONENT_IDS.items()}
        manifest = load(root / MANIFEST)
        approvals = validate_approvals(manifest, documents, validated, root)
        whole = manifest["globalAlgorithmSourceGate"] == "verified" and not any(missing.values())
        if require_approved:
            require(whole, "Whole E06 source gate remains pending; fixed27 approvals required")
        if with_upstream:
            import upstream
            lock = load(root / "UPSTREAM.json")
            upstream.verify_source(root / ".local/upstream-elkjs", lock)
            upstream.verify_package(root / ".local/npm-elkjs/package", lock)
            canonical = {}
            for lane, doc in [*documents.items(), ("default-unmerged", load(root / UNMERGED))]:
                blobs = {s["sourceId"]: upstream.git(root / ".local/upstream-elkjs", "show", s["commit"] + ":" + s["path"]) for s in doc["sources"]}
                for s in doc["sources"]:
                    require(upstream.git(root / ".local/upstream-elkjs", "rev-parse", s["commit"] + ":" + s["path"]).decode().strip() == s["gitBlob"], "Actual canonical Git blob differs")
                canonical[lane] = validate_canonical(doc, blobs)
                validate_function_line_alignment(doc, blobs)
                canonical[lane].update(validate_symbol_bindings(doc, blobs))
        require(all(sha256(contained(root, p)) == h for p, h in fingerprints.items()), "Source/review inputs changed during validation; rerun after stability")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e06-source-validation/v1", "status": "FAIL" if errors else "E06_SOURCE_BINDINGS_VALIDATED" if whole else "E06_SOURCE_BINDINGS_PARTIAL",
            "errors": errors, "componentCounts": counts, "expectedComponentCounts": {lane: len(ids) for lane, ids in FINAL_COMPONENT_IDS.items()},
            "fullDenominatorFrozen": True, "missingProposedComponentIds": missing, "approvedEvidence": approvals,
            "wholeSourceApproved": whole and not errors, "canonicalVerified": bool(with_upstream and not errors), "canonical": canonical,
            "inputSha256": fingerprints, "validatorSha256": sha256(Path(__file__)), "runtimeAcceptanceAssessed": False,
            "mathematicalEquivalenceAutomaticallyProved": False, "pythonAlgorithmsVerified": 0,
            "limitation": "Offline checks fixed identities, proof closure and independent approvals. Canonical Git/npm/LF/UTF16/lexical calls need --with-upstream. No ignored observations or engine execution required. Source acceptance is separate from runtime/math equivalence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true")
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--out", type=Path, help="New output JSON file; never overwrite evidence")
    args = parser.parse_args()
    result = check(with_upstream=args.with_upstream, require_approved=args.require_approved)
    if args.out:
        write(args.out, result)
    print(json.dumps(result, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
