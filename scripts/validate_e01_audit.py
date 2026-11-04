"""Check E01 source/path/assertion evidence and parallel iteration consistency.

Default checks are offline. --with-upstream additionally verifies the immutable
local source/npm artifact and every source range in the normalized port map.
Neither mode certifies a Python layout implementation or a release license.
"""
from __future__ import annotations

import argparse
import hashlib
import keyword
from pathlib import Path
import re

from layout_checks import ROOT, contained, diff, load, sha256, write


def check_plan(root: Path):
    errors = []
    plan = load(root / "docs/iteration-plan.json")
    iterations = plan["iterations"] + plan["integration"]
    nodes = {item["id"]: item for item in iterations}
    if len(nodes) != len(iterations):
        errors.append("Duplicate iteration ID")
    if set(nodes) != {f"E{i:02}" for i in range(1, 22)} | {f"I{i}" for i in range(4)}:
        errors.append("Iteration denominator differs")
    if plan["firstReleaseIterations"] != [f"E{i:02}" for i in range(1, 13)]:
        errors.append("First-release iteration denominator differs")
    if plan["mermaidIntegrationRequiredForFirstRelease"] is not False:
        errors.append("Standalone integration policy differs")
    coordination = plan["coordination"]
    if (coordination["maxActiveAgents"], coordination["maxSubagents"]) != (4, 3):
        errors.append("Parallel slot limits differ")
    if not coordination["stableValidationBarrierRequired"] or not coordination["retrospectiveRequired"]:
        errors.append("Stable validation and retrospective are required")
    protocol = contained(root / "docs", coordination["protocolDocument"]).read_text(encoding="utf-8")

    def check_evidence(label, items):
        if not isinstance(items, list) or not items:
            errors.append("Evidence is required: " + label)
            return
        for item in items:
            try:
                if not isinstance(item, dict) or not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
                    raise ValueError("Invalid evidence identity")
                if sha256(contained(root, item["path"])) != item["sha256"]:
                    raise ValueError("Evidence SHA256 mismatch")
            except (ValueError, KeyError, OSError) as error:
                errors.append(label + ": " + str(error))
    gates = {g["id"]: g for g in plan["gates"]}
    for gate in gates.values():
        if gate["status"] not in plan["gateStates"] or gate["ownerIteration"] not in nodes:
            errors.append("Invalid gate state/owner: " + gate["id"])
        if gate["status"] == "verified":
            if not gate.get("evidence"):
                errors.append("Verified gate requires evidence: " + gate["id"])
            check_evidence("gate " + gate["id"], gate.get("evidence"))
    work = set(re.findall(r"^\| (M\d-\d{2}|I[0-3]) \|", (root / "docs/TASKS.md").read_text(encoding="utf-8"), re.M))
    covered = set()
    for item in iterations:
        if item["status"] not in plan["iterationStates"]:
            errors.append("Unknown iteration state: " + item["id"])
        if item.get("parallelStrategy") != item["id"]:
            errors.append("Missing per-iteration parallel strategy: " + item["id"])
        if not re.search(r"^\| " + re.escape(item["id"]) + r"\b", protocol, re.M):
            errors.append("Parallel strategy table is missing iteration: " + item["id"])
        if not set(item["requiredGates"]) <= gates.keys() or not set(item["dependsOn"]) <= nodes.keys():
            errors.append("Unknown dependency/gate: " + item["id"])
        covered.update(item["workPackages"])
        if item["status"] == "complete":
            if any(nodes[dep]["status"] != "complete" for dep in item["dependsOn"] if dep in nodes):
                errors.append("Complete iteration has incomplete dependencies: " + item["id"])
            if any(gates[g]["status"] != "verified" for g in item["requiredGates"] if g in gates):
                errors.append("Complete iteration has unverified gates: " + item["id"])
            check_evidence("iteration " + item["id"], item.get("evidence"))
            if not item.get("evidence") or not item.get("retrospective"):
                errors.append("Complete iteration requires evidence and retrospective: " + item["id"])
            else:
                try:
                    if item["retrospective"] != "retrospectives/" + item["id"] + ".md":
                        raise ValueError("Retrospective must belong to its iteration")
                    retro = contained(root / "docs", item["retrospective"]).read_text(encoding="utf-8")
                    if not re.search(r"^# " + re.escape(item["id"]) + r"\b", retro, re.M) or not all(title in retro for title in ("## 交付与验收", "## 并行执行", "## 问题与改进", "## 下一轮")):
                        raise ValueError("Retrospective is missing required review sections")
                except (ValueError, OSError) as error:
                    errors.append(item["id"] + ": " + str(error))
    if work - covered != {"M0-01", "M0-02", "M0-03"} or covered - work:
        errors.append("Implementation work-package coverage differs")
    seen, visiting = set(), set()

    def visit(identity):
        if identity in visiting:
            errors.append("Iteration dependency cycle: " + identity)
            return
        if identity in seen or identity not in nodes:
            return
        visiting.add(identity)
        item = nodes[identity]
        dependencies = item["dependsOn"] + [gates[g]["ownerIteration"] for g in item["requiredGates"] if g in gates]
        for dep in dependencies:
            visit(dep)
        visiting.remove(identity)
        seen.add(identity)

    for identity in nodes:
        visit(identity)
    if plan["nextIteration"] not in nodes:
        errors.append("Unknown next iteration")
    def has_integration_dependency(identity, trail):
        if identity in trail or identity not in nodes:
            return False
        return any(dep.startswith("I") or has_integration_dependency(dep, trail | {identity}) for dep in nodes[identity]["dependsOn"])
    if any(has_integration_dependency(identity, set()) for identity in plan["firstReleaseIterations"]):
        errors.append("Standalone package must precede integration")
    return errors


def check(root: Path = ROOT, *, with_upstream=False):
    errors = []
    try:
        errors.extend(check_plan(root))
        manifest = load(root / "references/e01-audit.json")
        lock = load(root / "UPSTREAM.json")
        if manifest["baseline"]["commit"] != lock["javascript"]["commit"] or manifest["baseline"]["version"] != lock["javascript"]["version"]:
            errors.append("Audit baseline differs from source lock")
        if manifest["pythonAlgorithmsVerified"] != 0:
            errors.append("A source audit cannot certify Python algorithms")
        required = {"references/port-map.json", "references/layered-default-path.json",
                    "references/e01-source-lineage.json", "references/assertion-inventory.json"}
        if not required <= manifest["filesSha256"].keys():
            errors.append("Missing E01 evidence denominator")
        for name, digest in manifest["filesSha256"].items():
            if sha256(contained(root, name)) != digest:
                errors.append("Audit artifact SHA256 mismatch: " + name)
        mapping = load(root / "references/port-map.json")
        path_audit = load(root / "references/layered-default-path.json")
        lineage = load(root / "references/e01-source-lineage.json")
        if path_audit["baseline"]["commit"] != lock["javascript"]["commit"] or lineage["baseline"]["elkjsCommit"] != lock["javascript"]["commit"]:
            errors.append("Path/lineage baseline differs")
        sources = {s["id"]: s for s in mapping["sources"]}
        if len(sources) != len(mapping["sources"]):
            errors.append("Duplicate source ID")
        expected_sources = {s["id"]: s for s in path_audit["sources"]}
        if sources.keys() != expected_sources.keys():
            errors.append("Normalized source denominator differs")
        for identity, source in sources.items():
            expected = expected_sources.get(identity)
            if (not expected or any(source[k] != expected[k] for k in ("path", "sha256"))
                    or source["kind"] not in ("elkjs-git", "npm-artifact")
                    or (source["kind"] == "elkjs-git" and source["commit"] != lock["javascript"]["commit"])):
                errors.append("Normalized source identity differs: " + identity)
        inventory = load(root / "references/assertion-inventory.json")
        import audit_assertions
        audit_assertions.validate_snapshot(inventory, root)
        assertion_ids = {item["id"] for item in inventory["projectCases"]}
        for source in inventory["sources"]:
            for case in source["testCases"]:
                assertion_ids.add(case["id"])
                assertion_ids.update(site["id"] for site in case["assertionSites"])
        for source in sources.values():
            known = lock["sourceSha256"].get(source["path"], lock["distribution"]["sha256Files"].get(source["path"]))
            if known and source["sha256"] != known:
                errors.append("Normalized source differs from lock: " + source["id"])
        expected_components = ({"entry:" + entry["id"] for entry in path_audit["entryPath"]}
                               | {"processor:" + p["generatedClass"] for p in path_audit["processorCatalog"]}
                               | {"option:" + o["id"] for o in path_audit["options"]} | {"model:id-values"})
        component_ids = [item["id"] for item in mapping["components"]]
        if len(component_ids) != len(set(component_ids)) or set(component_ids) != expected_components or mapping["totals"]["mappedComponents"] != len(component_ids):
            errors.append("Port-map component denominator/identity differs")
        sequence = [p["generatedClass"] for p in path_audit["defaultFlatProcessorSequence"]]
        if mapping["defaultSingleEdgeSequence"] != sequence or mapping["totals"]["defaultSingleEdgeCalls"] != len(sequence):
            errors.append("Default processor sequence differs")
        profiles = load(root / "docs/release-profiles.json")
        expected_options = set(profiles["profiles"][0]["options"])
        if len(path_audit["options"]) != len(expected_options) or {o["id"] for o in path_audit["options"]} != expected_options:
            errors.append("Nine-option audit denominator differs")
        by_component = {component["id"]: component for component in mapping["components"]}
        for option in path_audit["options"]:
            component = by_component.get("option:" + option["id"])
            if component and not diff(component.get("declaredDefault"), option["layeredDeclaredDefault"])["passed"]:
                errors.append("Mapped option default differs: " + option["id"])
            if component and component.get("metadataTargets") != option["metadataTargets"]:
                errors.append("Mapped option scope differs: " + option["id"])
        calls = sum(o["processorCalls"] for o in path_audit["observations"])
        observed_classes = {name for o in path_audit["observations"] for name in o["processorClassSequence"]}
        totals = path_audit["totals"]
        if (totals["sampledRequests"] != len(path_audit["observations"]) or totals["freshEngineProcesses"] != 3 * len(path_audit["observations"])
                or totals["processorBeforeCalls"] != calls or totals["processorAfterCalls"] != calls
                or totals["uniqueProcessorClasses"] != len(observed_classes)
                or observed_classes != {p["generatedClass"] for p in path_audit["processorCatalog"]}):
            errors.append("Path observation denominator differs")
        if any(item != 0 for item in (path_audit["pythonAlgorithmsVerified"], lineage["pythonAlgorithmsVerified"], mapping["totals"]["pythonAlgorithmsVerified"])):
            errors.append("Source/path maps cannot certify Python algorithms")
        audited_spans = {}
        def collect_spans(value):
            if isinstance(value, dict):
                if {"sourceId", "lineStart", "lineEnd", "spanSha256"} <= value.keys():
                    audited_spans[(value["sourceId"], value["lineStart"], value["lineEnd"])] = value["spanSha256"]
                for child in value.values():
                    collect_spans(child)
            elif isinstance(value, list):
                for child in value:
                    collect_spans(child)
        collect_spans(path_audit)
        def valid_citation(cite):
            if cite["sourceId"] not in sources or cite["lineStart"] < 1 or cite["lineEnd"] < cite["lineStart"]:
                return False
            return (cite["lineEnd"] <= sources[cite["sourceId"]]["lineCount"]
                    and isinstance(cite.get("symbol"), str) and bool(cite["symbol"])
                    and bool(re.fullmatch(r"[0-9a-f]{64}", cite.get("spanSha256", ""))))
        for component in mapping["components"]:
            if not component["sourceRefs"] or not component["assertionRefs"] or not component["pythonTargets"]:
                errors.append("Incomplete port mapping: " + component["id"])
            for cite in component["sourceRefs"]:
                if not valid_citation(cite):
                    errors.append("Invalid source range: " + component["id"])
                known_span = audited_spans.get((cite["sourceId"], cite["lineStart"], cite["lineEnd"]))
                if known_span and known_span != cite.get("spanSha256"):
                    errors.append("Source span differs from path audit: " + component["id"])
            if not set(component["assertionRefs"]) <= assertion_ids:
                errors.append("Unknown assertion reference: " + component["id"])
            for target in component["pythonTargets"]:
                if target["status"] != "planned" or target.get("existsClaimed", False) is not False:
                    errors.append("E01 symbols must remain planned: " + component["id"])
                symbol = target.get("symbol")
                if not isinstance(symbol, str) or not symbol or not all(part.isidentifier() and not keyword.iskeyword(part) for part in symbol.split(".")):
                    errors.append("Invalid planned Python symbol: " + component["id"])
            if component.get("assertionRelationship") != "topic_only":
                errors.append("E01 assertion links must remain topic-only: " + component["id"])
        if with_upstream:
            import upstream
            upstream.verify_source(root / ".local/upstream-elkjs", lock)
            upstream.verify_package(root / ".local/npm-elkjs/package", lock)
            canonical = {}
            for source in sources.values():
                if source["kind"] == "elkjs-git":
                    data = upstream.git(root / ".local/upstream-elkjs", "show", source["commit"] + ":" + source["path"])
                elif source["kind"] == "npm-artifact":
                    data = contained(root / ".local/npm-elkjs/package", source["path"]).read_bytes()
                else:
                    raise ValueError("Unknown normalized source kind")
                if hashlib.sha256(data).hexdigest() != source["sha256"]:
                    errors.append("Canonical source SHA256 mismatch: " + source["id"])
                if len(data.splitlines()) != source["lineCount"]:
                    errors.append("Canonical source line count differs: " + source["id"])
                canonical[source["id"]] = data.decode("utf-8").splitlines()
            for component in mapping["components"]:
                for cite in component["sourceRefs"]:
                    if not valid_citation(cite):
                        continue
                    span = "\n".join(canonical[cite["sourceId"]][cite["lineStart"] - 1:cite["lineEnd"]]) + "\n"
                    if hashlib.sha256(span.encode("utf-8")).hexdigest() != cite["spanSha256"]:
                        errors.append("Canonical source span SHA256 mismatch: " + component["id"])
                    if cite["symbol"] not in span:
                        errors.append("Source symbol not in cited span: " + component["id"])
    except (ValueError, KeyError, TypeError, OSError) as error:
        errors.append(str(error))
    return {"status": "E01_AUDIT_VALIDATED" if not errors else "FAIL", "errors": errors,
            "withUpstream": with_upstream, "pythonAlgorithmsVerified": 0,
            "limitation": "E01 evidence/coordination checks only; not Python algorithm, full assertion coverage or release acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = check(with_upstream=args.with_upstream)
    if args.out:
        write(args.out, result)
    import json
    print(json.dumps(result, indent=2))
    return bool(result["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
