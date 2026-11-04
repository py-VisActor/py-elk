"""Audit E04 source identities, evidence links and optional canonical bytes.

Default checks are offline and do not require .git, .local or Node. Canonical
Git/npm/span/function/callsite checks require --with-upstream. Neither mode
automatically proves the mathematical equivalence of an extracted branch or
accepts a Python layout, PRNG sequence, public API or distribution license.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from layout_checks import ROOT, contained, diff, load, sha256, write
from source_read_cache import readonly_source_check

SCHEMA = "py-elk-e04-component-sources/v1"
ADR = "docs/decisions/0003-e04-generated-source-slice.md"
DOCUMENTS = {lane: f"references/e04-source-components-{lane}.json" for lane in ("A", "B")}
SOURCES = {
    "elkjs-generated-worker": ("lib/elk-worker.js", "canonical-generated-artifact"),
    "elkjs-package": ("package.json", "fixed-elkjs-source"),
    "elkjs-license": ("LICENSE.md", "fixed-elkjs-source"),
    "elkjs-readable-json-adapter": ("src/java-additional/org/eclipse/elk/graph/json/JsonAdapter.xtend", "fixed-elkjs-source"),
}
INTERMEDIATES = {
    "EdgeAndLayerConstraintEdgeReverser": (0, "$process_7"), "LayerConstraintPreprocessor": (2, "$process_32"),
    "LayerConstraintPostprocessor": (4, "$process_31"), "LongEdgeSplitter": (5, "$process_35"),
    "PortSideProcessor": (6, "$process_44"), "PortListSorter": (7, "$process_43"),
    "InLayerConstraintProcessor": (10, "$process_21"), "LabelAndNodeSizeProcessor": (11, "$process_25"),
    "InnermostNodeMarginCalculator": (12, "$process_22"), "LayerSizeAndGraphHeightCalculator": (14, "$process_33"),
    "LongEdgeJoiner": (16, "$process_34"), "EndLabelSorter": (17, "$process_10"), "ReversedEdgeRestorer": (18, "$process_46"),
}
A_COMPONENTS = {"intermediate:" + name: ("intermediate", index, (symbol,)) for name, (index, symbol) in INTERMEDIATES.items()}
A_COMPONENTS.update({
    "graph:ordered-layered-model": ("graph", None, ("LGraph", "LNode", "LPort", "LEdge", "$setSource_0", "$setTarget_0", "$setLayer_0", "$setNode")),
    "import:json-to-layered": ("import", None, ("$createLGraph", "$importGraph_1", "$importFlatGraph", "$transformNode", "$transformEdge", "createPort", "getDirection_1")),
    "export:layered-to-json": ("export", None, ("$applyLayout_2", "$applyNodeLayout", "$applyEdgeLayout", "$applyParentNodeLayout", "$lambda$37", "$transferShapeLayout")),
    "conditional:GraphTransformer": ("conditional-intermediate", None, ("$process_12",)),
})
B_COMPONENTS = {
    "phase:GREEDY": ("phase", 1, ("$process_62",)), "phase:NETWORK_SIMPLEX": ("phase", 3, ("$process_73",)),
    "phase:LAYER_SWEEP_BARYCENTER": ("phase", 8, ("$process_76",)), "phase:LAYER_SWEEP_GREEDY_SWITCH": ("phase", 9, ("$process_76",)),
    "phase:BRANDES_KOEPF": ("phase", 13, ("$process_82",)), "phase:ORTHOGONAL": ("phase", 15, ("$process_84",)),
    "support:generated-JavaRandom": ("random-support", None, ("$nextInternal", "$nextDouble", "$nextInt", "$nextLong", "$setSeed", "$setSeed_0", "Random", "Random_0")),
}
HOST_PROOFS = {"HOST-GWT", "HOST-MATH-PROPERTY", "ordered-identity-graph"}
DISPOSITIONS = {
    "A": {"host-map-runtime-or-collections", "host-map-explicit-math-properties-or-data", "algorithm-effect-covered-by-source-guard-proof", "host-map-explicit-ordered-model"},
    "B": {"generated-runtime-host-mapping", "algorithm-effect-covered-by-slice-proof", "fixed-generated-rng-equations"},
}
HEX = re.compile(r"[0-9a-f]{64}")
JS_NAME = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return type(value) is str and bool(value.strip())


def texts(value, *, empty=False):
    return type(value) is list and (empty or bool(value)) and all(nonempty(item) for item in value)


def walk(value, path=""):
    if type(value) is dict:
        yield path, value
        for key, child in value.items():
            yield from walk(child, path + "/" + key)
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from walk(child, path + "/" + str(index))


def span_records(document):
    return [(path, item) for path, item in walk(document) if {"sourceId", "symbol", "startLine", "endLine", "spanSha256"} <= item.keys()]


def edge_records(document):
    return [(path, item) for path, item in walk(document) if {"caller", "callee", "callSiteLines", "calleeSpan"} <= item.keys()]


def range_records(document):
    """Explicit ranges lacking a function/span checksum still need bounds."""
    result = [(item["sourceId"], item["startLine"], item["endLine"]) for _, item in walk(document)
              if {"sourceId", "startLine", "endLine"} <= item.keys()]
    for source in document["sources"]:
        for span in source.get("lineRanges", []):
            result.append((source["sourceId"], span["startLine"], span["endLine"]))
    for _, item in walk(document):
        for key in ("lineRange", "sourceRange"):
            if key in item:
                value = item[key]
                require(type(value) is list and len(value) == 2, "Invalid explicit source range pair")
                result.append(("elkjs-generated-worker", value[0], value[1]))
    return result


def validate_span_shape(span, source_ids):
    require(span["sourceId"] in source_ids and nonempty(span["symbol"]), "Unknown source or empty span symbol")
    start, end = span["startLine"], span["endLine"]
    require(type(start) is int and type(end) is int and 1 <= start <= end, "Invalid or boolean source line number")
    require(type(span["spanSha256"]) is str and bool(HEX.fullmatch(span["spanSha256"])), "Invalid source span SHA")
    fields = {"functionStartOffset", "functionEndOffset", "functionSha256", "offsetUnit"}
    if fields & span.keys():
        require(fields <= span.keys(), "Incomplete exact function/offset receipt")
        a, b = span["functionStartOffset"], span["functionEndOffset"]
        require(type(a) is int and type(b) is int and 0 <= a < b and span["offsetUnit"] == "UTF-16 code units", "Function offsets must be explicit UTF16 units")
        require(type(span["functionSha256"]) is str and bool(HEX.fullmatch(span["functionSha256"])), "Invalid exact function SHA")


def validate_document(document, lock, lane):
    require(document["schema"] == SCHEMA and document["lane"] == lane, "E04 source schema/lane differs")
    expected_status = "slice-source-bindings-awaiting-independent-review" if lane == "A" else "source-proof-proposals-ready-for-independent-review"
    require(document["status"] == expected_status, "Frozen source proposal status differs")
    baseline = {"package": "elkjs", "version": lock["javascript"]["version"], "commit": lock["javascript"]["commit"],
                "workerSha256": lock["distribution"]["sha256Files"]["lib/elk-worker.js"],
                "bundledSha256": lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]}
    require(diff(document["baseline"], baseline)["passed"], "E04 fixed source baseline differs")
    require(type(document["pythonAlgorithmsVerified"]) is int and document["pythonAlgorithmsVerified"] == 0
            and document["nativeLayoutImplemented"] is False and document["algorithmSourceGate"] == "unverified", "Historical source proposals cannot claim runtime/global acceptance")
    for _, item in walk(document):
        for field in ("nativeLayoutImplemented", "runtimeAccepted", "legalCompatibilityConclusion"):
            if field in item:
                require(item[field] is False, "Nested source metadata cannot promote runtime/license acceptance")
        if "pythonAlgorithmsVerified" in item:
            require(type(item["pythonAlgorithmsVerified"]) is int and item["pythonAlgorithmsVerified"] == 0, "Nested source metadata cannot certify algorithms")
    if lane == "A":
        candidate = document["candidates"]
        require(candidate["actualPortSource"] is False and candidate["workerBuildCorrespondence"] == "unresolved"
                and candidate["role"] == "readable explanatory headers only", "Candidate Java cannot masquerade as the exact port source")
    expected_sources = set(SOURCES) if lane == "A" else set(SOURCES) - {"elkjs-readable-json-adapter"}
    sources = document["sources"]
    require(type(sources) is list and len(sources) == len(expected_sources) and {s["sourceId"] for s in sources} == expected_sources, "E04 source denominator differs")
    known = {**lock["sourceSha256"], **lock["distribution"]["sha256Files"]}
    for source in sources:
        path, kind = SOURCES[source["sourceId"]]
        require(source["path"] == path and source["kind"] == kind and source["commit"] == lock["javascript"]["commit"]
                and source["sha256"] == known[path], "E04 source role/path/kind/commit/SHA differs")
    expected_components = A_COMPONENTS if lane == "A" else B_COMPONENTS
    components = document["components"]
    require(type(components) is list and len(components) == len(expected_components) and {c["componentId"] for c in components} == set(expected_components), "E04 component denominator differs")
    proof_ids = set(expected_components)
    for component in components:
        role, index, entry = expected_components[component["componentId"]]
        require(component["role"] == role and component.get("defaultCallIndex") == index, "Component role/default position differs")
        if index is not None:
            require(type(component["defaultCallIndex"]) is int, "Boolean processor index")
        spans = component["entrySpans"]
        require(type(spans) is list and bool(spans) and set(entry) <= {s["symbol"] for s in spans}, "Required source entry disappeared or changed")
        require(texts(component["reads"]) and texts(component["writes"]), "Component field obligations cannot be vacuous")
        if "sliceDerivation" in component:
            proof = component["sliceDerivation"]
            require(nonempty(proof["id"]) and proof["id"] not in proof_ids and proof["kind"] == "fixed-source-constrained-equivalence-proposal", "Invalid/duplicate source derivation identity")
            require(texts(proof.get("steps", [])) or (type(proof.get("guards")) is list and bool(proof["guards"])), "Source derivation has no stated guard/reasoning")
            proof_ids.add(proof["id"])
        elif role in ("intermediate", "conditional-intermediate"):
            require(nonempty(component.get("sliceBranch", component.get("observationScope"))), "Missing component guard")
    if lane == "A":
        host = document["hostMappingProofs"]
        require(type(host) is list and len(host) == 3 and {p["id"] for p in host} == HOST_PROOFS, "Host proof registry denominator differs")
        for proof in host:
            expected_kind = "explicit-host-representation" if proof["id"] == "ordered-identity-graph" else "explicit-host-support-mapping"
            require(proof["kind"] == expected_kind, "Host mapping kind differs")
            require(texts(proof["semantics"]) and texts(proof["retainedWrites"]) and texts(proof["excludedClaims"])
                    and type(proof["sourceSpans"]) is list and bool(proof["sourceSpans"]), "Host mapping lacks explicit obligations/source")
            if "componentRefs" in proof:
                require(texts(proof["componentRefs"]) and set(proof["componentRefs"]) <= set(expected_components), "Unknown host representation component")
        proof_ids |= HOST_PROOFS
    helper_count = 0
    for component in components:
        helpers = component.get("observedHelpers", component.get("observedTransitiveHelperDispositions", []))
        require(type(helpers) is list, "Helper dispositions must be an array")
        if component["componentId"] != "conditional:GraphTransformer" and component["role"] != "random-support":
            require(bool(helpers), "Active component helper inventory disappeared")
        for helper in helpers:
            require(helper["disposition"] in DISPOSITIONS[lane] and helper["proofRef"] in proof_ids, "Unresolved helper disposition/proofRef")
            helper_count += 1
    spans = span_records(document)
    require(bool(spans), "Source span inventory disappeared")
    for _, span in spans:
        validate_span_shape(span, expected_sources)
    for identity, start, end in range_records(document):
        require(identity in expected_sources and type(start) is int and type(end) is int and 1 <= start <= end, "Invalid explicit source range")
    for _, edge in edge_records(document):
        require(type(edge["caller"]) is str and bool(JS_NAME.fullmatch(edge["caller"])) and type(edge["callee"]) is str and bool(JS_NAME.fullmatch(edge["callee"])), "Invalid static caller/callee symbol")
        require(type(edge["callSiteLines"]) is list and bool(edge["callSiteLines"]) and all(type(line) is int and line >= 1 for line in edge["callSiteLines"]), "Static callsite lines are invalid")
        require(edge["callee"] == edge["calleeSpan"]["symbol"], "Static edge/callee span identity differs")
    license_record = document["licenseEvidence"]
    require(license_record["declaredSpdx"] == "EPL-2.0 OR GPL-3.0-or-later" and license_record["legalCompatibilityConclusion"] is False
            and license_record["projectDistributionLicense"] == "unresolved", "Source declaration cannot claim distribution-license closure")
    return {"components": len(components), "helperOccurrences": helper_count, "spanOccurrences": len(spans),
            "staticCallEdges": len(edge_records(document)), "proofIds": sorted(proof_ids)}


def validate_canonical(document, raw_sources):
    """Pure byte/span/function/callsite checker; tests can supply tiny fixtures."""
    rows, utf16 = {}, {}
    for source in document["sources"]:
        raw = raw_sources[source["sourceId"]]
        require(hashlib.sha256(raw).hexdigest() == source["sha256"], "Canonical source SHA differs")
        text = raw.decode("utf-8")
        rows[source["sourceId"]] = text.splitlines()
        utf16[source["sourceId"]] = text.encode("utf-16-le")
    for identity, start, end in range_records(document):
        require(identity in rows and type(start) is int and type(end) is int and 1 <= start <= end <= len(rows[identity]), "Canonical source range out of bounds")
    by_symbol, offsets = {}, 0
    for _, span in span_records(document):
        validate_span_shape(span, rows.keys())
        identity = span["sourceId"]
        start, end = span["startLine"], span["endLine"]
        require(end <= len(rows[identity]), "Canonical source span out of bounds")
        raw = ("\n".join(rows[identity][start - 1:end]) + "\n").encode("utf-8")
        require(hashlib.sha256(raw).hexdigest() == span["spanSha256"], "Canonical LF span SHA differs")
        by_symbol.setdefault((identity, span["symbol"]), set()).add((start, end))
        if "functionStartOffset" in span:
            a, b = span["functionStartOffset"], span["functionEndOffset"]
            require(b <= len(utf16[identity]) // 2, "Canonical UTF16 function offset out of bounds")
            try:
                function = utf16[identity][a * 2:b * 2].decode("utf-16-le").encode("utf-8")
            except UnicodeError as error:
                raise ValueError("Function offset splits a UTF16 code point") from error
            require(hashlib.sha256(function).hexdigest() == span["functionSha256"], "Canonical UTF16 function SHA differs")
            offsets += 1
    for _, edge in edge_records(document):
        identity = edge["calleeSpan"]["sourceId"]
        require(edge["callee"] == edge["calleeSpan"]["symbol"], "Call edge/callee identity differs")
        callers = by_symbol.get((identity, edge["caller"]), ())
        require(bool(callers), "Static caller has no bounded source receipt")
        token = re.compile(r"(?<![\w$])" + re.escape(edge["callee"]) + r"\s*\(")
        for line in edge["callSiteLines"]:
            require(type(line) is int and 1 <= line <= len(rows[identity]) and bool(token.search(rows[identity][line - 1])), "Static callee token missing at canonical callsite")
            require(any(start <= line <= end for start, end in callers), "Static callsite outside caller receipt")
    return {"sources": len(rows), "spanOccurrences": len(span_records(document)), "functionOffsetOccurrences": offsets,
            "staticCallEdges": len(edge_records(document)), "classification": "lexical source binding, not dynamic reachability/equivalence"}


def validate_approved_evidence(root, documents, manifest=None):
    """Bind versioned reviews; never require ignored historical run paths."""
    root = Path(root)
    manifest = load(root / "references/e04-component-approvals.json") if manifest is None else manifest
    require(manifest["schema"] == "py-elk-e04-component-approvals/v1" and manifest["scopeDocument"] == ADR
            and manifest["scopeDocumentSha256"] == sha256(root / ADR), "Approval scope document differs")
    expected = {**{identity: "A" for identity in A_COMPONENTS}, **{identity: "B" for identity in B_COMPONENTS}}
    approvals = manifest["approvals"]
    require(type(approvals) is list and len(approvals) == len(expected) and {a["componentId"] for a in approvals} == set(expected), "Source approval denominator differs")
    reviews = {}
    for item in approvals:
        lane = expected[item["componentId"]]
        source_path = DOCUMENTS[lane]
        expected_review = "references/e04-reviews/" + ("A-source-by-V.json" if lane == "A" else "B-source-by-A.json")
        require(item["sourceDocument"] == source_path and item["sourceDocumentSha256"] == sha256(root / source_path), "Approved source document SHA differs")
        require(item["versionedReview"] == expected_review and item["versionedReviewSha256"] == sha256(contained(root, expected_review)), "Versioned source review differs")
        require(item["runtimeAccepted"] is False, "Source approval cannot certify runtime acceptance")
        status = "verified-exclusion-guarded-out" if item["componentId"] == "conditional:GraphTransformer" else "verified-for-component-porting"
        require(item["status"] == status, "Approved component port/exclusion category differs")
        if expected_review not in reviews:
            reviewed = load(root / expected_review)
            require(reviewed["status"] == "ACCEPTED_UNDER_ADR0003_GUARDS", "Source review is not accepted")
            references = reviewed["reviewedFiles"]
            require(any(r["path"] == source_path and r["sha256"] == item["sourceDocumentSha256"] for r in references), "Review does not bind the approved source")
            approved = reviewed["portingAuthorizationRecommendation"] if lane == "A" else reviewed["approvedSourceComponents"]
            required = set(A_COMPONENTS) - {"conditional:GraphTransformer"} if lane == "A" else set(B_COMPONENTS)
            require(type(approved) is list and len(approved) == len(required) and set(approved) == required, "Review-approved component denominator differs")
            blockers = reviewed["remainingBlockingFindings"] if lane == "A" else reviewed["remainingBSourceBlockers"]
            require(blockers == [], "Source review contains unresolved blockers")
            reviews[expected_review] = reviewed
    require(set(manifest["licenseSha256"]) == {"src/pyelk/_licenses/elkjs-LICENSE.md", "src/pyelk/_licenses/NOTICE.md"}, "Packaged notice denominator differs")
    for path, fingerprint in manifest["licenseSha256"].items():
        require(sha256(contained(root, path)) == fingerprint, "Actual packaged notice SHA differs")
    license_record = documents["A"]["licenseEvidence"]["portNoticePolicy"]
    require(license_record["status"] == "actual-files-byte-verified" and len(license_record["licensePaths"]) == 2, "A notice evidence is not sealed")
    require({r["path"]: r["sha256"] for r in license_record["licensePaths"]} == manifest["licenseSha256"], "Source/approval notice fingerprints disagree")
    return {"approvedComponentBindings": len(approvals), "versionedReviews": sorted(reviews), "ignoredRunFilesRequired": False}


@readonly_source_check
def check(root=ROOT, *, with_upstream=False):
    root = Path(root)
    errors, statistics, canonical, approvals = [], {}, None, None
    try:
        lock = load(root / "UPSTREAM.json")
        documents = {lane: load(root / path) for lane, path in DOCUMENTS.items()}
        for lane, document in documents.items():
            statistics[lane] = validate_document(document, lock, lane)
        approvals = validate_approved_evidence(root, documents)
        if with_upstream:
            import upstream
            checkout = root / ".local/upstream-elkjs"
            upstream.verify_source(checkout, lock)
            upstream.verify_package(root / ".local/npm-elkjs/package", lock)
            canonical = {}
            for lane, document in documents.items():
                blobs = {s["sourceId"]: upstream.git(checkout, "show", s["commit"] + ":" + s["path"]) for s in document["sources"]}
                canonical[lane] = validate_canonical(document, blobs)
            license_bytes = upstream.git(checkout, "show", lock["javascript"]["commit"] + ":LICENSE.md")
            require((root / "src/pyelk/_licenses/elkjs-LICENSE.md").read_bytes() == license_bytes, "Packaged license is not the exact locked upstream file")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e04-source-bindings-validation/v1", "status": "E04_SOURCE_BINDINGS_VALIDATED" if not errors else "FAIL",
            "errors": errors, "offlineStructure": statistics, "approvedEvidence": approvals, "canonical": canonical,
            "canonicalVerified": with_upstream and not errors, "runtimeAcceptanceAssessed": False,
            "mathematicalEquivalenceAutomaticallyProved": False, "pythonAlgorithmsVerified": 0,
            "limitation": "Source identity/structure/review bindings only. Canonical spans/functions/calls are checked only with --with-upstream; lexical calls are not observed reachability. Candidate headers and ignored raw traces are historical review evidence, not re-executed here. No legal distribution or runtime acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true")
    parser.add_argument("--out", type=Path, help="New output file; existing evidence is never overwritten")
    args = parser.parse_args()
    report = check(with_upstream=args.with_upstream)
    if args.out:
        write(args.out, report)
    print(json.dumps({key: report[key] for key in ("status", "errors", "canonicalVerified", "pythonAlgorithmsVerified")}, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
