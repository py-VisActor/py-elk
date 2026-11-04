"""Verify E05 source bindings and explicit approvals; never approve or run layout.

Default validation permits a structurally valid partial proposal. A full
denominator must be frozen in this script before --require-approved can succeed.
Canonical mode alone reads the fixed local Git/npm artifacts; offline mode uses
only versioned files and does not require ignored observations, Node or Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from layout_checks import ROOT, contained, load, sha256, write
from source_read_cache import readonly_source_check
from validate_e04_source_bindings import edge_records, span_records, validate_canonical, validate_span_shape, walk

DOCUMENTS = {lane: f"references/e05-source-components-{lane}.json" for lane in "AB"}
DOCUMENTS["R"] = "references/e05-source-routing.json"
MANIFEST = "references/e05-component-approvals.json"
SCOPE = "docs/decisions/0004-e05-dag-long-edge.md"
ENCODING = "UTF-8 JSON, sort_keys=True, ensure_ascii=True, separators=(comma,colon), no trailing newline"
BASELINE = {"package": "elkjs", "version": "0.12.1", "commit": "624ae90aa37110033a8af59c5ccbb292708b4317",
            "workerSha256": "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86"}
SOURCE_IDENTITIES = {
    "elkjs-generated-worker": ("lib/elk-worker.js", "13d07b8601ca22b5de216ca7e8f497a61335a22d", BASELINE["workerSha256"]),
    "elkjs-package": ("package.json", "56c7fa4f29e7d3807d39f750334013760a0d6eaa", "2cf15ab73c358103ac1bdb94ff4ede887c5ca3efaf3d579ade4b7c289eca3bc5"),
    "elkjs-license": ("LICENSE.md", "91dd37eefbe62d3d9fb7a1e7e2c7a9a1e2cdcbcc", "637e81f4a1b6b4079535c499fca05e238cf7605c1ff5b76d60d7da7ce96700c9"),
}
REQUIRED_PARTIAL = {"A": {"graph:indexed-target", "intermediate:LongEdgeSplitter", "intermediate:LongEdgeJoiner", "phase:NETWORK_SIMPLEX"},
                    "B": {"phase:GREEDY"}, "R": {"phase:ORTHOGONAL"}}
FINAL_COMPONENT_IDS = {
    "A": {"graph:indexed-target", "phase:NETWORK_SIMPLEX", "import:json-to-layered", "export:layered-to-json"} |
         {"intermediate:" + name for name in (
             "LongEdgeSplitter", "LongEdgeJoiner", "PortSideProcessor", "PortListSorter", "LabelAndNodeSizeProcessor",
             "InnermostNodeMarginCalculator", "EdgeAndLayerConstraintEdgeReverser", "LayerConstraintPreprocessor",
             "LayerConstraintPostprocessor", "InLayerConstraintProcessor", "LayerSizeAndGraphHeightCalculator",
             "EndLabelSorter", "ReversedEdgeRestorer")},
    "B": {"phase:GREEDY", "phase:LAYER_SWEEP_BARYCENTER", "phase:LAYER_SWEEP_GREEDY_SWITCH", "phase:BRANDES_KOEPF"},
    "R": {"phase:ORTHOGONAL"},
}
# These five approvals were independently accepted before the remaining source
# proposals. Removing them cannot relabel the current checkout as an earlier wave.
REQUIRED_APPROVAL_IDS = REQUIRED_PARTIAL["A"] | REQUIRED_PARTIAL["B"]
NS_SEAL = "b5e6ade9ab0d4d224f1424287c65139d119f2de82808cc9198d7994146795292"
NS_DEPENDENTS = {"phase:LAYER_SWEEP_BARYCENTER", "phase:LAYER_SWEEP_GREEDY_SWITCH", "phase:BRANDES_KOEPF"}
INHERITED = {
    "references/e04-source-components-A.json": "680adba43629a854f8226039fe3a11e1beb4e755014bfee7077cf7a1b414a05b",
    "references/e04-source-components-B.json": "1760ed7b3ea09a6f369d27095cbfc26cb44feeeefd55ffe691372c5892947cff",
}
AUXILIARY = {"references/e05-routing-numeric-observations.json": "py-elk-e05-routing-number-oracle/v1"}
LICENSES = {"src/pyelk/_licenses/elkjs-LICENSE.md": SOURCE_IDENTITIES["elkjs-license"][2],
            "src/pyelk/_licenses/NOTICE.md": "ede5bce9ab6ed6577a9db063fb3248d40ffb6b1cc6e0d83c1f79f1ce21674db6",
            "src/pyelk/_licenses/NOTICE-E05.md": "db8b3b0213999ebfddf7e8dbb358864038274156528b447ba56ef47bab549807"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
# These four narrative consequences supplement existing bounded proofs. They are
# not independent source lemmas and are never advertised as machine-proven math.
SUPPLEMENTAL_PROOFS = {
    ("intermediate:LabelAndNodeSizeProcessor", "NS5-G8-HELPER-CLOSURE"):
        {"NS5-G" + str(n) + suffix for n, suffix in (
            (1, "-NORMAL-FILTER"), (2, "-GIVEN-CELL-HEIGHT"), (3, "-ALIGNMENT-DEFUSE"),
            (4, "-ORDERED-CONTEXTS"), (5, "-SINGLE-AND-MULTIPORT-FLOAT"),
            (6, "-PROPERTY-DEFAULT-GATES"), (7, "-CLONE-AND-EMPTY-LABELS"))},
    ("intermediate:InnermostNodeMarginCalculator", "MG-G2-TINY-OVERSHOOT"):
        {"MG-G1-REAL-UNION", "NS5-G5-SINGLE-AND-MULTIPORT-FLOAT"},
    ("import:json-to-layered", "IMP-G3-CARDINALITY"):
        {"IMP-G1-ORDER-AND-IDENTITY", "NS-G6-SPLIT-SCALE"},
    ("export:layered-to-json", "EXP-G4-MODEL-DENOMINATOR"):
        {"EXP-G1-LAYER-CLEANUP-COMBINE", "EXP-G2-EDGE-CHAIN-AND-JUNCTION",
         "EXP-G3-ORIGINAL-JSON-ORDER", "LE-JOIN-G1", "LE-JOIN-G2"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return type(value) is str and bool(value.strip())


def digest(value):
    require(type(value) is str and bool(HASH.fullmatch(value)), "Invalid SHA256")


def exact_zero(value):
    require(type(value) is int and value == 0, "Source evidence cannot claim a complete Python algorithm count")


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()


def source_context(document):
    return {"baseline": document["baseline"], "sources": [{key: value for key, value in row.items() if key != "localPath"}
                                                          for row in document["sources"]]}


def no_runtime_claims(value):
    fields = {"nativeLayoutImplemented", "nativeExpansionImplemented", "nativeRuntimeAccepted", "runtimeAccepted",
              "runtimeAcceptanceAssessed", "fullAlgorithmAccepted", "publicLayoutApiAccepted", "lifecycleAccepted",
              "releaseAccepted", "packagePublished", "concurrencyAccepted", "cancellationAccepted"}
    for _, item in walk(value):
        for name in fields & item.keys():
            require(item[name] is False, "Source-only metadata promotes runtime capability: " + name)
        if "pythonAlgorithmsVerified" in item:
            exact_zero(item["pythonAlgorithmsVerified"])


def json_pointer(document, pointer):
    require(type(pointer) is str and (not pointer or pointer.startswith("/")), "Invalid inherited proof JSON pointer")
    value = document
    for part in pointer.split("/")[1:]:
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if type(value) is list else value[key]
    require(type(value) in (dict, list) and bool(value), "Inherited proof pointer is vacuous")
    return value


def inherited_artifacts(component, root):
    records = {}
    for _, item in walk(component):
        key = "artifact" if "artifact" in item else "immutableSupportEvidence" if "immutableSupportEvidence" in item else None
        if key is None:
            continue
        artifact = item[key]
        require(type(artifact) is dict and {"path", "sha256"} <= artifact.keys() and
                set(artifact) <= {"path", "sha256", "purpose"}, "Invalid inherited proof artifact")
        path = artifact["path"]
        require(path in INHERITED or path in AUXILIARY, "Unregistered source/proof/evidence dependency")
        if path in INHERITED:
            require(artifact["sha256"] == INHERITED[path], "Inherited source/proof identity differs")
        else:
            # Observations support the included static proof; this does not
            # turn the numeric bridge into an algorithm source or runtime input.
            evidence = load(contained(root, path))
            require(evidence["schema"] == AUXILIARY[path] and evidence["workerSha256"] == BASELINE["workerSha256"] and
                    type(evidence["records"]) is list and len(evidence["records"]) == 7, "Numeric observation identity/denominator differs")
            require(type(evidence["compareNegativePositiveZero"]) is int and evidence["compareNegativePositiveZero"] == -1,
                    "Numeric signed-zero observation differs")
            no_runtime_claims(evidence)
        require(sha256(contained(root, path)) == artifact["sha256"], "Inherited shared proof bytes changed")
        if "jsonPointer" in item:
            json_pointer(load(root / path), item["jsonPointer"])
        if "componentId" in item:
            inherited = load(root / path)
            require(item["componentId"] in {c["componentId"] for c in inherited["components"]}, "Inherited component reference does not resolve")
        records[path] = artifact["sha256"]
    return [{"path": path, "sha256": records[path]} for path in sorted(records)]


def validate_document(document, lane, root=ROOT):
    require(document["schema"] == "py-elk-e05-component-sources/v1" and document["lane"] == lane, "E05 source schema/lane differs")
    require(document["baseline"] == BASELINE and all(type(document["baseline"][k]) is str for k in BASELINE), "Fixed source baseline differs")
    require(document["algorithmSourceGate"] in ("unverified", "unverified-for-E05-expansion"), "Proposal cannot approve the whole source gate")
    require(document["nativeLayoutImplemented"] is False, "Source proposal is not a runtime implementation claim")
    exact_zero(document["pythonAlgorithmsVerified"])
    no_runtime_claims(document)
    expected_sources = {"elkjs-generated-worker", "elkjs-license"} | ({"elkjs-package"} if lane == "A" else set())
    sources = document["sources"]
    require(type(sources) is list and len(sources) == len(expected_sources), "Fixed source denominator differs")
    by_source = {row["sourceId"]: row for row in sources}
    require(len(by_source) == len(sources) and set(by_source) == expected_sources, "Fixed source roles differ")
    for identity, row in by_source.items():
        keys = {"sourceId", "path", "commit", "gitBlob", "sha256", "kind" if lane == "A" else "role"}
        require(keys <= row.keys() and set(row) <= keys | {"localPath"}, "Canonical source identity receipt fields differ: " + identity)
        path, blob, fingerprint = SOURCE_IDENTITIES[identity]
        require((row["path"], row["gitBlob"], row["sha256"], row["commit"]) == (path, blob, fingerprint, BASELINE["commit"]), "Canonical source identity differs: " + identity)
        if lane == "A":
            require(row["kind"] == ("canonical-generated-artifact" if identity == "elkjs-generated-worker" else "fixed-elkjs-source"), "Source kind differs")
        else:
            require(row["role"] == ("direct-generated-algorithm-source" if identity == "elkjs-generated-worker" else "upstream-original-license"), "Source role differs")
    components = document["components"]
    require(type(components) is list and components, "No source components")
    by_component = {row["componentId"]: row for row in components}
    require(len(by_component) == len(components) and REQUIRED_PARTIAL[lane] <= by_component.keys(), "Known partial component denominator differs")
    require(set(by_component) <= FINAL_COMPONENT_IDS[lane], "Unexpected whole-slice component identity")
    seals = {}
    document_proofs = {(c["componentId"], p["id"]) for c in components
                       for p in c.get("sourceDerivation", c.get("guardProofs", []))}
    for identity, component in by_component.items():
        require(nonempty(identity), "Empty component identity")
        for key in ("reads", "writes"):
            require(type(component[key]) is list and component[key] and all(nonempty(v) for v in component[key]), "Component has vacuous " + key)
        if lane == "A":
            require(component["status"] == "ready-for-independent-source-review", "A component is not ready")
            require(component["actualPortSource"] == by_source["elkjs-generated-worker"], "Component and shared source registry differ")
            require(component["unresolved"] == [], "Component has unresolved own source obligations")
            hosts = component.get("hostMappings", [])
            if hosts:
                expected_hosts = ({"NS-HOST-PRIVATE-GRAPH", "NS-HOST-COLLECTIONS", "NS-HOST-SCALARS"}
                                  if identity == "phase:NETWORK_SIMPLEX" else
                                  {"E05-HOST-ORDERED-IDENTITY", "E05-HOST-PROPERTIES", "E05-HOST-VECTORS-COLLECTIONS"})
                require(type(hosts) is list and len(hosts) == 3 and {h["id"] for h in hosts} == expected_hosts, "Embedded host proof denominator differs")
            else:
                require(type(component.get("inheritedSourceBindings")) is dict and
                        type(component.get("immutableHostSupport")) is list and component["immutableHostSupport"], "A component has no host proof closure")
            for host in hosts:
                require(nonempty(host["semantics"]) and type(host["sourceSpans"]) is list and host["sourceSpans"] and
                        type(host["retainedWrites"]) is list and host["retainedWrites"] and all(nonempty(v) for v in host["retainedWrites"]), "Embedded host proof is vacuous")
                for span in host["sourceSpans"]:
                    validate_span_shape(span, by_source)
            derivations = component.get("sourceDerivation", component.get("guardProofs"))
            require(type(derivations) is list and derivations and len({p["id"] for p in derivations}) == len(derivations), "Source derivation IDs missing or duplicated")
            for proof in derivations:
                require(nonempty(proof["id"]) and nonempty(proof["proof"]), "Source derivation is vacuous")
                if "sourceRefs" not in proof:
                    anchors = SUPPLEMENTAL_PROOFS.get((identity, proof["id"]))
                    owners = {"NS5-G5-SINGLE-AND-MULTIPORT-FLOAT": "intermediate:LabelAndNodeSizeProcessor",
                              "NS-G6-SPLIT-SCALE": "phase:NETWORK_SIMPLEX",
                              "LE-JOIN-G1": "intermediate:LongEdgeJoiner",
                              "LE-JOIN-G2": "intermediate:LongEdgeJoiner"}
                    require(anchors is not None and
                            all((owners.get(anchor, identity), anchor) in document_proofs for anchor in anchors),
                            "Narrative consequence has no registered bounded proof anchors")
                    if proof["id"] == "NS5-G8-HELPER-CLOSURE":
                        require(type(component.get("newObservedHelperMappings")) is list and
                                len(component["newObservedHelperMappings"]) == 7,
                                "Helper consequence omits its seven bounded mappings")
                    continue
                require(type(proof["sourceRefs"]) is list and proof["sourceRefs"], "Source derivation is vacuous")
                for span in proof["sourceRefs"]:
                    validate_span_shape(span, by_source)
        else:
            allowed_status = ({"proposed-closed-under-explicit-work-graph-guards-awaiting-independent-review"} if lane == "R" else
                              {"proposed-closed-under-explicit-DAG-guards", "proposed-closed-under-explicit-proper-DAG-default-guards"})
            require(component["closureStatus"] in allowed_status and component["unresolved"] == [], "Component source closure is open")
            require(component["entrySpans"] and component["guardProofs"] and component["hostMappingRefs"], "B source proof is vacuous")
            proofs = component["guardProofs"]
            require(type(proofs) is list and len({p["id"] for p in proofs}) == len(proofs) and
                    all(nonempty(p["id"]) and nonempty(p["kind"]) and nonempty(p["claim"]) for p in proofs), "Guard proof identity/claim differs")
            symbols = {span["symbol"] for _, span in span_records(component)}
            for proof in proofs:
                if "sourceSymbols" in proof:
                    require(type(proof["sourceSymbols"]) is list and proof["sourceSymbols"] and
                            all(s in symbols for s in proof["sourceSymbols"]), "Guard proof cites an unbound source symbol")
                else:
                    evidence = proof.get("evidenceRefs")
                    require((type(evidence) is list and evidence and all(nonempty(v) for v in evidence)) or
                            nonempty(proof.get("dependentLemma")), "Guard proof has no source/evidence role")
                    # A narrative dependentLemma remains manually reviewed text;
                    # it is not advertised as an automatically resolved proofRef.
        if "plannedPythonModule" in component:
            require(nonempty(component["plannedPythonModule"]) and
                    (component.get("existsClaimed") is False if lane != "A" else
                     ("existsClaimed" not in component or component["existsClaimed"] is False) and
                     component.get("nativeExpansionImplemented") is False),
                    "Planned Python module cannot claim an implementation")
            module_path = PurePosixPath(component["plannedPythonModule"])
            require(module_path.parts[:2] == ("src", "pyelk") and module_path.suffix == ".py" and
                    module_path.as_posix() == component["plannedPythonModule"] and module_path.stem.isidentifier() and
                    all(part.isidentifier() for part in module_path.parts[2:-1]), "Invalid planned Python module path")
        local_proofs = {proof["id"] for key in ("hostMappings", "sourceDerivation", "guardProofs") for proof in component.get(key, [])}
        for _, item in walk(component):
            for key in ("proofRef", "proofRefs"):
                if key in item:
                    refs = [item[key]] if key == "proofRef" else item[key]
                    require(type(refs) is list and refs and all(nonempty(ref) and ref in local_proofs for ref in refs), "Unresolved component-local proof reference")
        notices = component["licenseRefs"]
        require(type(notices) is list and notices, "Component omits license references")
        if lane != "A" and all(type(ref) is str for ref in notices):
            # B's explicit source-ID form resolves through the fixed source
            # registry. Global approval still binds all actual packaged notices.
            expected_notices = {"elkjs-license", "elkjs-generated-worker"} if lane == "R" else {"elkjs-license"}
            require(len(notices) == len(set(notices)) and set(notices) == expected_notices and set(notices) <= by_source.keys(), "Component license source role differs")
            require(sha256(root / "src/pyelk/_licenses/elkjs-LICENSE.md") == by_source["elkjs-license"]["sha256"], "Actual source license differs")
        else:
            require(all(type(ref) is dict for ref in notices), "Mixed or invalid license reference representation")
            for notice in notices:
                require(notice["path"] in LICENSES and notice["sha256"] == LICENSES[notice["path"]] and
                        sha256(contained(root, notice["path"])) == notice["sha256"], "Component license binding differs")
            require({r["path"] for r in notices} >= set(LICENSES) - {"src/pyelk/_licenses/NOTICE-E05.md"}, "Component omits original source notices")
        inherited_artifacts(component, root)
        seals[identity] = canonical_sha(component)
    if "componentSeals" in document:
        require(document["componentSeals"] == seals, "Declared component seals differ")
    for _, span in span_records(document):
        validate_span_shape(span, by_source)
    for _, edge in edge_records(document):
        require(nonempty(edge["caller"]) and nonempty(edge["callee"]) and type(edge["callSiteLines"]) is list and edge["callSiteLines"] and
                all(type(n) is int and n > 0 for n in edge["callSiteLines"]), "Static callsite identity/lines are vacuous")
        require(edge["callee"] == edge["calleeSpan"]["symbol"], "Static callee identity differs")
    require(bool(span_records(document)), "No source span bindings")
    return {"components": by_component, "seals": seals, "sources": by_source}


def validate_function_line_alignment(document, raw_sources):
    """Tie each exact UTF16 function slice to its own LF span, not another body."""
    text = {key: raw.decode("utf-8") for key, raw in raw_sources.items()}
    utf16 = {key: value.encode("utf-16-le") for key, value in text.items()}
    rows = {key: value.splitlines() for key, value in text.items()}
    for _, span in span_records(document):
        if "functionStartOffset" not in span:
            continue
        source = utf16[span["sourceId"]]
        a, b = span["functionStartOffset"], span["functionEndOffset"]
        start_line = source[:a * 2].decode("utf-16-le").count("\n") + 1
        end_line = source[:b * 2].decode("utf-16-le").count("\n") + 1
        require((start_line, end_line) == (span["startLine"], span["endLine"]), "Exact function slice and LF span describe different source lines")
    for _, item in walk(document):
        if "assignment" not in item:
            continue
        span = item.get("sourceSpan", item.get("span"))
        require(type(span) is dict and nonempty(item["assignment"]) and
                re.fullmatch(r"[$A-Za-z_][\w$]*\s*=\s*\S.*;", item["assignment"].strip()), "Declaration excerpt has no exact assignment binding")
        excerpt = "\n".join(rows[span["sourceId"]][span["startLine"] - 1:span["endLine"]])
        require(item["assignment"].strip() in excerpt, "Declared assignment contradicts the canonical source excerpt")


def review_binding(review, row, identity):
    if row["lane"] == "A":
        require(review["schema"] == "py-elk-e05-component-source-review/v1" and review["reviewer"] == "V" and review["reviewedLane"] == "A"
                and review["status"] == "ACCEPTED_UNDER_COMPONENT_GUARDS" and review["blockers"] == [], "A independent source review differs")
        require(review["sourceDocument"] == {"path": row["sourceDocument"], "sha256": row["sourceDocumentSha256AtReview"]}, "A reviewed source receipt differs")
        approved, seals = review["approvedComponents"], review["componentSeals"]
        require(review["nativeRuntimeAccepted"] is False and review["wholeE05SourceGateApproved"] is False, "Partial review promotes whole gate/runtime")
    else:
        expected_status = ("ACCEPTED_UNDER_COMPONENT_GUARDS" if identity in
                           {"phase:LAYER_SWEEP_BARYCENTER", "phase:LAYER_SWEEP_GREEDY_SWITCH", "phase:BRANDES_KOEPF"}
                           else "ACCEPTED_UNDER_EXPLICIT_DAG_GUARDS")
        require(review["schema"] == "py-elk-e05-independent-component-review/v1" and review["reviewerLane"] == ("A" if row["lane"] == "B" else "B")
                and review["status"] == expected_status and review["remainingBlockingFindings"] == [], "B/R independent source review differs")
        require({"path": row["sourceDocument"], "sha256": row["sourceDocumentSha256AtReview"]} in review["reviewedFiles"], "B reviewed source receipt differs")
        approved, seals = review["approvedSourceComponents"], review["approvedComponentSeals"]
        require(review["runtimeAcceptanceAssessed"] is False, "Source review claims runtime acceptance")
        if identity in NS_DEPENDENTS - {"phase:BRANDES_KOEPF"}:
            dependency = review.get("dependency")
            require(type(dependency) is dict and set(dependency) == {"componentId", "canonicalComponentSha256", "basis"}
                    and dependency["componentId"] == "phase:NETWORK_SIMPLEX" and
                    dependency["canonicalComponentSha256"] == NS_SEAL and nonempty(dependency["basis"]),
                    "LayerSweep independent review dependency differs")
    require(type(approved) is list and len(approved) == len(set(approved)) and identity in approved and
            set(seals) == set(approved) and seals[identity] == row["canonicalComponentSha256"], "Independent review approved component/seal differs")
    no_runtime_claims(review)


def versioned_review_paths(manifest):
    paths = set()
    for row in manifest["approvals"]:
        paths.add(row["versionedReview"])
        for entry in row.get("approvalHistory", []):
            paths.add(entry["previousApproval"]["versionedReview"])
    return paths


def validate_approval_history(row, review, root):
    """Bind the BK scope amendment to its original full, versioned source review.

    The historical raw-run path is diagnostic; it is never required offline.
    This validates the explicit review chain, not a mathematical diff proof.
    """
    history = row.get("approvalHistory", [])
    if row["componentId"] != "phase:BRANDES_KOEPF":
        require(history == [] and "priorFullReview" not in review, "Unexpected source approval amendment")
        return
    require(type(history) is list and len(history) == 1 and nonempty(history[0]["reason"]), "BK full-source approval history missing")
    previous = history[0]["previousApproval"]
    require(previous["componentId"] == row["componentId"] and previous["lane"] == "B" and
            previous["status"] == "verified-for-component-porting" and previous["runtimeAccepted"] is False and
            previous["sourceDocument"] == DOCUMENTS["B"] and
            previous["canonicalComponentSha256"] == "5182ee6ba518e97caf6ce2809c74dfe2d73a78f7c2f832340852d22fd5725e28" and
            previous["sourceDocumentSha256AtReview"] == previous["sourceDocumentSha256AtApproval"] ==
            "19f2ad313e9aef80181fc38331984e06f730f09c492b9110a668de2c710f0499" and
            previous["sourceContextSha256"] == row["sourceContextSha256"] and
            previous["inheritedArtifacts"] == row["inheritedArtifacts"] and
            previous["componentDependencies"] == {"phase:NETWORK_SIMPLEX": NS_SEAL},
            "BK previous full-source approval identity differs")
    path = previous["versionedReview"]
    require(path == "references/e05-reviews/BRANDES_KOEPF-by-A.json" and
            previous["versionedReviewSha256"] == sha256(contained(root, path)), "BK previous full review bytes differ")
    full_review = load(root / path)
    require("priorFullReview" not in full_review, "BK full review cannot be only another amendment")
    review_binding(full_review, previous, row["componentId"])
    prior = review.get("priorFullReview")
    require(type(prior) is dict and set(prior) == {"path", "sha256"} and nonempty(prior["path"]) and
            prior["sha256"] == previous["versionedReviewSha256"] and
            review.get("changedFieldsOnly") == ["scope", "configurationHelperSpans", "guardProofs"],
            "BK amendment does not bind the full prior review")


def validate_context_history(row, document):
    history = row.get("sourceContextHistory", [])
    # This E05 initial GREEDY receipt was reviewed before its auxiliary LICENSE
    # Git blob was recorded. Preserve the one explicitly authorized transition.
    if row["lane"] == "B" and row["componentId"] == "phase:GREEDY":
        require(type(history) is list and len(history) == 1, "Initial GREEDY context transition history is missing")
    else:
        require(history == [], "Unexpected source context history needs independent review")
        return
    current = source_context(document)
    old = json.loads(json.dumps(current))
    next(s for s in old["sources"] if s["sourceId"] == "elkjs-license").pop("gitBlob")
    transition = history[0]
    require(transition["previousSha256"] == canonical_sha(old) and transition["currentSha256"] == canonical_sha(current)
            and transition["currentSha256"] == row["sourceContextSha256"], "Source context history chain differs")
    digest(transition["sourceDocumentSha256"])
    require(nonempty(transition["reason"]) and nonempty(transition["updatedUtc"]), "Missing context transition explanation")
    expected = [{key: source[key] for key in ("sourceId", "path", "gitBlob", "sha256")} for source in document["sources"]]
    require(transition["canonicalSourceIdentityChecks"] == expected, "Context history cannot loosen fixed source identities")


def validate_approvals(manifest, documents, validated, root):
    require(manifest["schema"] == "py-elk-e05-component-approvals/v1" and manifest["iteration"] == "E05", "E05 approval schema differs")
    require(manifest["status"] == ("E05_SOURCE_SCOPE_VERIFIED" if manifest["globalAlgorithmSourceGate"] == "verified" else "E05_SOURCE_SCOPE_PENDING"), "Whole-source status/gate category differs")
    require(manifest["scopeDocument"] == SCOPE and manifest["scopeDocumentSha256"] == sha256(root / SCOPE), "Current scope binding differs")
    require(manifest["componentEncoding"] == ENCODING, "Component canonical encoding differs")
    require(manifest["licenseSha256"] == LICENSES, "Approval license denominator or identity differs")
    for path, fingerprint in LICENSES.items():
        require(sha256(contained(root, path)) == fingerprint, "Packaged license bytes changed")
    rows = manifest["approvals"]
    require(type(rows) is list and len({r["componentId"] for r in rows}) == len(rows), "Approval component identity duplicate")
    require(REQUIRED_APPROVAL_IDS <= {r["componentId"] for r in rows}, "Known independently accepted component approvals are missing")
    by_approval = {row["componentId"]: row for row in rows}
    for row in rows:
        lane, identity = row["lane"], row["componentId"]
        require(lane in DOCUMENTS and identity in validated[lane]["components"] and row["sourceDocument"] == DOCUMENTS[lane], "Approval source/component identity differs")
        require(row["status"] == "verified-for-component-porting" and row["runtimeAccepted"] is False, "Component approval promotes runtime")
        for key in ("sourceDocumentSha256AtApproval", "sourceDocumentSha256AtReview", "canonicalComponentSha256", "sourceContextSha256", "scopeDocumentSha256AtApproval", "versionedReviewSha256"):
            digest(row[key])
        require(row["canonicalComponentSha256"] == validated[lane]["seals"][identity], "Approved component/dependency seal changed")
        require(row["sourceContextSha256"] == canonical_sha(source_context(documents[lane])), "Shared source context changed without an explicit receipt update")
        expected_dependencies = {"phase:NETWORK_SIMPLEX": NS_SEAL} if identity in NS_DEPENDENTS else {}
        require(row.get("componentDependencies", {}) == expected_dependencies, "Approved component dependency differs")
        for dependency, fingerprint in expected_dependencies.items():
            require(dependency in by_approval and by_approval[dependency]["canonicalComponentSha256"] == fingerprint and
                    validated["A"]["seals"][dependency] == fingerprint, "Component dependency is not the actual approved source")
        validate_context_history(row, documents[lane])
        require(row["inheritedArtifacts"] == inherited_artifacts(validated[lane]["components"][identity], root), "Inherited proof closure receipt differs")
        review_path = row["versionedReview"]
        require(type(review_path) is str and review_path.startswith("references/e05-reviews/") and sha256(contained(root, review_path)) == row["versionedReviewSha256"], "Versioned independent review bytes differ")
        review = load(root / review_path)
        review_binding(review, row, identity)
        validate_approval_history(row, review, root)
    if manifest["globalAlgorithmSourceGate"] == "verified":
        require(manifest.get("finalSourceDocumentsSha256") ==
                {DOCUMENTS[lane]: sha256(root / DOCUMENTS[lane]) for lane in DOCUMENTS},
                "Whole-source final document bytes differ")
    no_runtime_claims(manifest)
    return {"approvedComponents": len(rows), "componentIds": [r["componentId"] for r in rows], "wholeDenominatorFrozen": FINAL_COMPONENT_IDS is not None}


@readonly_source_check
def check(root=ROOT, *, with_upstream=False, require_approved=False):
    root = Path(root)
    errors, counts, canonical, approvals, pending_lanes, fingerprints, missing = [], {}, None, None, [], {}, {}
    whole = False
    try:
        pending_lanes = [lane for lane, path in DOCUMENTS.items() if not (root / path).is_file()]
        require(not (set(pending_lanes) - {"R"}), "Required existing source proposal is missing")
        initial_paths = [path for lane, path in DOCUMENTS.items() if lane not in pending_lanes]
        initial_paths += [MANIFEST, SCOPE, *INHERITED, *LICENSES]
        initial_paths += [path for path in AUXILIARY if (root / path).is_file()]
        fingerprints = {path: sha256(contained(root, path)) for path in initial_paths}
        documents = {lane: load(root / path) for lane, path in DOCUMENTS.items() if lane not in pending_lanes}
        validated = {lane: validate_document(doc, lane, root) for lane, doc in documents.items()}
        identities = [identity for value in validated.values() for identity in value["components"]]
        require(len(set(identities)) == len(identities), "Source component belongs to two lanes")
        counts = {lane: len(value["components"]) for lane, value in validated.items()}
        manifest = load(root / MANIFEST)
        for path in versioned_review_paths(manifest):
            fingerprints[path] = sha256(contained(root, path))
        approvals = validate_approvals(manifest, documents, validated, root)
        missing = {lane: sorted(expected - set(validated.get(lane, {}).get("components", {}))) for lane, expected in FINAL_COMPONENT_IDS.items()}
        whole = (not any(missing.values()) and manifest["globalAlgorithmSourceGate"] == "verified" and
                 {r["componentId"] for r in manifest["approvals"]} == set().union(*FINAL_COMPONENT_IDS.values()))
        if require_approved:
            require(not pending_lanes, "A source lane remains pending")
            require(not any(missing.values()), "Frozen whole-slice component denominator is incomplete")
            require(manifest["globalAlgorithmSourceGate"] == "verified" and manifest["status"] == "E05_SOURCE_SCOPE_VERIFIED", "Whole E05 source gate remains pending")
            require({r["componentId"] for r in manifest["approvals"]} == set().union(*FINAL_COMPONENT_IDS.values()), "Whole component approval denominator differs")
        else:
            require(manifest["globalAlgorithmSourceGate"] in ("verified", "unverified-for-E05-expansion"), "Unknown whole-source gate claim")
            require(manifest["globalAlgorithmSourceGate"] != "verified" or whole, "Whole-source approval does not cover the fixed22 components")
        if with_upstream:
            import upstream
            lock = load(root / "UPSTREAM.json")
            upstream.verify_source(root / ".local/upstream-elkjs", lock)
            upstream.verify_package(root / ".local/npm-elkjs/package", lock)
            canonical = {}
            for lane, doc in documents.items():
                blobs = {s["sourceId"]: upstream.git(root / ".local/upstream-elkjs", "show", s["commit"] + ":" + s["path"]) for s in doc["sources"]}
                for s in doc["sources"]:
                    blob = upstream.git(root / ".local/upstream-elkjs", "rev-parse", s["commit"] + ":" + s["path"]).decode().strip()
                    require(blob == s["gitBlob"], "Actual canonical Git blob differs")
                canonical[lane] = validate_canonical(doc, blobs)
                validate_function_line_alignment(doc, blobs)
        require(all(sha256(contained(root, path)) == value for path, value in fingerprints.items()), "Source/review inputs changed during validation; rerun after owner stability")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e05-source-validation/v1", "status": "FAIL" if errors else "E05_SOURCE_BINDINGS_VALIDATED" if whole else "E05_SOURCE_BINDINGS_PARTIAL",
            "errors": errors, "componentCounts": counts, "approvedEvidence": approvals, "canonical": canonical,
            "canonicalVerified": with_upstream and not errors and not pending_lanes,
            "presentProposalCanonicalVerified": with_upstream and not errors, "pendingLanes": pending_lanes,
            "fullDenominatorFrozen": FINAL_COMPONENT_IDS is not None,
            "expectedComponentCounts": {lane: len(ids) for lane, ids in FINAL_COMPONENT_IDS.items()},
            "missingProposedComponentIds": missing, "wholeSourceApproved": whole and not errors,
            "inputSha256": fingerprints, "validatorSha256": sha256(Path(__file__)),
            "runtimeAcceptanceAssessed": False, "mathematicalEquivalenceAutomaticallyProved": False, "pythonAlgorithmsVerified": 0,
            "limitation": "Offline structure, fixed identities and explicit source approvals only; actual Git/npm/span/function/callsite checks require --with-upstream. Partial checks never approve the entire E05 gate or runtime. No ignored run files are needed."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true")
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--out", type=Path, help="New output file, never overwrite evidence")
    args = parser.parse_args()
    result = check(with_upstream=args.with_upstream, require_approved=args.require_approved)
    if args.out:
        write(args.out, result)
    print(json.dumps(result, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
