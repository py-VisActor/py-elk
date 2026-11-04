"""Offline E02 contract/profile/probe checks; optional fixed-source and probe replay.

Synthetic observations below test the comparator only. No Python layout engine is
implemented or certified by this script.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import inspect
import json
from pathlib import Path
import re

from layout_checks import ROOT, compare_captures, compare_observations, contained, diff, load, sha256, validate_json, write
from validate_e01_audit import check_plan

PROFILE = "native-basic-layered-v1"
SOURCE_IDS = {"elkjs-api", "elkjs-node-entry", "elkjs-java-bridge", "elkjs-worker-identity-hash",
              "elkjs-logging-reuse-test", "elkjs-options-test", "elkjs-worker-layered-defaults"}
FACT_IDS = {"OBS-NULL-01", "OBS-FALSY-01", "OBS-PRECEDENCE-01", "OBS-LOGGING-REUSE-01",
            "OBS-USER-HASH-COLLISION-01", "OBS-USER-HASH-PRESERVED-01", "OBS-ERROR-INPUT-01",
            "OBS-FAKEWORKER-LIFECYCLE-01", "OBS-CONSTRUCTOR-DEFAULT-OPTIONS-01"}


def validate_outcome(record):
    if record.get("outcome") not in ("returned", "threw") or record.get("returnStyle") not in ("promise", "synchronous", "synchronous_throw"):
        raise ValueError("Probe timeout/unknown outcome cannot count as captured")
    if record["outcome"] == "threw":
        error = record.get("error")
        if not isinstance(error, dict) or any(not isinstance(error.get(key), str) for key in ("name", "message")):
            raise ValueError("Thrown probe outcome requires exact error name/message")


def decode_request(encoded):
    raw = base64.b64decode(encoded, validate=True)
    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ValueError("Duplicate probe request key: " + key)
            data[key] = value
        return data
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError("Nonfinite JSON: " + token)))
    validate_json(value)
    return raw, value


def validate_probes(bundle, lock):
    if bundle.get("schema") != "py-elk-contract-probes/v1" or bundle.get("status") != "CAPTURED":
        raise ValueError("Contract probes are incomplete or invalid")
    if bundle["baseline"] != {"version": lock["javascript"]["version"], "commit": lock["javascript"]["commit"],
                               "entrypointSha256": lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]}:
        raise ValueError("Probe baseline differs")
    probes = bundle["probes"]
    if not probes or bundle["probeCount"] != len(probes) or len({p["id"] for p in probes}) != len(probes):
        raise ValueError("Probe denominator/identity differs")
    if type(bundle["pythonAlgorithmsVerified"]) is not int or bundle["pythonAlgorithmsVerified"] != 0:
        raise ValueError("Official probes cannot certify native Python")
    for probe in probes:
        raw, request = decode_request(probe["requestBytesBase64"])
        digest = hashlib.sha256(raw).hexdigest()
        observation = probe["observation"]
        process = probe["process"]
        if (probe["requestSha256"] != digest or observation["requestSha256"] != digest
                or not diff(request, probe["input"])["passed"]):
            raise ValueError("Probe original-byte fingerprint or parsed input differs: " + probe["id"])
        if (probe["id"] != request["id"] or probe["id"] != observation["id"]
                or probe["category"] != request["category"] or observation.get("schema") != "py-elk-contract-observation/v1"):
            raise ValueError("Probe ID is not bound to its request/observation")
        if type(process["exitCode"]) is not int or process["exitCode"] != 0 or process.get("signal") is not None or process.get("spawnError") is not None:
            raise ValueError("Failed probe process cannot count as captured")
        if not re.fullmatch(r"[0-9a-f]{64}", probe.get("rawObservationSha256", "")):
            raise ValueError("Missing raw observation fingerprint")
        engine = observation["engine"]
        if engine["name"] != "elkjs" or engine["version"] != lock["javascript"]["version"] or engine["entrypointSha256"] != bundle["baseline"]["entrypointSha256"]:
            raise ValueError("Probe engine identity differs")
        validate_outcome(observation["constructor"])
        if observation["constructor"]["outcome"] == "returned":
            if [call["id"] for call in observation["calls"]] != [call["id"] for call in request["calls"]]:
                raise ValueError("Probe call denominator differs")
            if [call["method"] for call in observation["calls"]] != [call["method"] for call in request["calls"]]:
                raise ValueError("Probe method differs from its request")
            cleanup = observation.get("finalTermination")
            if not isinstance(cleanup, dict) or cleanup.get("outcome") not in ("returned", "threw"):
                raise ValueError("Probe final termination is incomplete")
            validate_outcome(cleanup)
        elif observation["calls"]:
            raise ValueError("Failed constructor cannot provide successful call records")
        for call in observation["calls"]:
            validate_outcome(call)
    return {p["id"]: p for p in probes}


def validate_definition(definition, probes, lock):
    if (definition.get("schema") != "py-elk-native-contract/v1" or definition.get("profileId") != PROFILE
            or definition.get("status") != "frozen-design" or type(definition.get("revision")) is not int or definition["revision"] != 1):
        raise ValueError("Native contract is not the frozen v1 definition")
    if definition.get("evidenceSealStatus") != "sealed":
        raise ValueError("Contract evidence receipts are not sealed")
    expected = {"upstreamVersion": lock["javascript"]["version"], "upstreamCommit": lock["javascript"]["commit"],
                "entrypoint": "lib/elk.bundled.js", "entrypointSha256": lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]}
    if definition["baseline"] != expected:
        raise ValueError("Native contract baseline differs")
    claims = definition["runtimeClaims"]
    if set(claims) != {"implementationAvailable", "pythonAlgorithmAccepted", "publicApiAccepted", "lifecycleAccepted", "concurrencyAccepted", "cancellationAccepted"} or any(value is not False for value in claims.values()) or type(definition["pythonAlgorithmsVerified"]) is not int or definition["pythonAlgorithmsVerified"] != 0:
        raise ValueError("Contract design cannot claim runtime/API/lifecycle acceptance")
    context = definition["requestContext"]
    if context["requiredForNative"] is not True or set(context["acceptedPythonTypes"]) != {"pathlib.Path", "bytes"}:
        raise ValueError("Native profile must bind original request bytes")
    rules = {rule["id"]: rule for rule in definition["adaptations"]}
    if len(rules) != len(definition["adaptations"]) or set(rules) != {"NATIVE-INPUT-01", "GWT-SHAPE-HASH-01"}:
        raise ValueError("Native adaptation rule denominator differs")
    if rules["GWT-SHAPE-HASH-01"]["allowedReferencePaths"] != ["/result/$H", "/result/children/<original-index>/$H"]:
        raise ValueError("Reference field projection is broader than frozen shape paths")
    required_fields = {"profile", "exact", "coordinateTolerance", "rawStrict", "publicContract", "adaptations", "inputPreservation", "passed", "lifecycleObservations"}
    if not required_fields <= set(definition["reportContract"]["fields"]) or definition["reportContract"]["strictDefault"] != "strict" or definition["reportContract"]["lifecycleAcceptance"] != "NOT_ASSESSED":
        raise ValueError("Native comparison report hides strict/default/lifecycle boundaries")
    if definition["errorContract"]["comparison"] != "Exact, with no generic exception-class normalization or message stripping":
        raise ValueError("Native profile must not normalize unknown errors")
    if definition["errorContract"]["runtimeImplementation"] != "not_implemented":
        raise ValueError("Error contract is a design, not a runtime implementation")
    host = definition["hostDesign"]
    if any(host[key]["accepted"] is not False for key in ("termination", "concurrency", "cancellation")) or host["concurrency"]["cpuParallelismClaim"] is not False:
        raise ValueError("Nested host design cannot claim lifecycle/concurrency/cancellation acceptance")
    sources, facts = definition["sourceEvidence"], definition["observations"]
    if len(sources) != len(SOURCE_IDS) or {s["sourceId"] for s in sources} != SOURCE_IDS:
        raise ValueError("Contract source evidence denominator differs")
    if len(facts) != len(FACT_IDS) or {fact["id"] for fact in facts} != FACT_IDS:
        raise ValueError("Contract observation evidence denominator differs")
    for fact in definition["observations"]:
        if fact.get("pythonRuntimeTested") is not False:
            raise ValueError("Official observations cannot claim Python runtime tests")
        if (not fact["sourceIds"] or len(set(fact["sourceIds"])) != len(fact["sourceIds"])
                or not set(fact["sourceIds"]) <= SOURCE_IDS or not fact["probes"]
                or len({p["probeId"] for p in fact["probes"]}) != len(fact["probes"])):
            raise ValueError("Contract fact lacks unique source/probe references")
        for citation in fact["probes"]:
            probe = probes.get(citation["probeId"])
            if not probe or any(citation[k] != probe[k] for k in ("requestSha256", "rawObservationSha256")):
                raise ValueError("Contract fact refers to a different probe receipt")
    keys = ("requestContext", "scope", "adaptations", "protectedFields", "errorContract", "reportContract", "hostDesign")
    rule_bytes = json.dumps({key: definition[key] for key in keys}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(rule_bytes).hexdigest() != definition["evidenceSeal"]["rulesSha256"]:
        raise ValueError("Frozen comparison rule fingerprint differs")


def profile_smoke(root=ROOT):
    """Synthetic positive/negative controls, explicitly not an engine implementation."""
    case_root = root / "references/layout/layered-diamond-right"
    request_path = case_root / "request.json"
    request = load(request_path)
    reference = load(case_root / "run-01/observation.json")
    candidate = copy.deepcopy(reference)
    candidate["engine"] = {"name": "pyelk", "version": "SYNTHETIC-COMPARATOR-CONTROL"}
    for before, result in [(request["graph"], candidate["result"]), *zip(request["graph"]["children"], candidate["result"]["children"])]:
        if "$H" not in before:
            result.pop("$H", None)
    candidate["inputAfter"] = copy.deepcopy(request["graph"])
    candidate["constructorAfter"] = copy.deepcopy(request["constructor"])
    candidate["argumentsAfter"] = copy.deepcopy(request["layoutArguments"])
    compared = compare_observations(reference, candidate, profile=PROFILE, request=request_path)
    if not compared["passed"] or compared["rawStrict"]["coordinateTolerance"]["passed"] or not compared["adaptations"] or compared["lifecycleObservations"]["acceptance"] != "NOT_ASSESSED":
        raise ValueError("Native profile smoke control hides raw differences or fails its positive")
    altered = copy.deepcopy(candidate)
    altered["result"]["children"][0]["x"] += 1
    if compare_observations(reference, altered, profile=PROFILE, request=request_path)["passed"]:
        raise ValueError("Native profile accepted a coordinate corruption")
    altered = copy.deepcopy(candidate)
    altered["inputAfter"]["children"][0]["width"] += 1e-10
    if compare_observations(reference, altered, profile=PROFILE, request=request_path)["passed"]:
        raise ValueError("Native profile applied tolerance to caller input preservation")
    return {"status": "SYNTHETIC_PROFILE_CONTROLS_PASS", "pythonAlgorithmsVerified": 0}


def validate_manifest(manifest, definition, bundle):
    if manifest.get("schema") != "py-elk-e02-audit/v1" or manifest.get("status") != "AUDIT_BATCH_COMPLETE":
        raise ValueError("E02 audit is not sealed")
    if (manifest["profileId"] != PROFILE or type(manifest["pythonAlgorithmsVerified"]) is not int
            or manifest["pythonAlgorithmsVerified"] != 0 or not diff(manifest["runtimeClaims"], definition["runtimeClaims"])["passed"]):
        raise ValueError("E02 audit cannot claim native Python acceptance")
    if not diff(manifest["baseline"], definition["baseline"])["passed"]:
        raise ValueError("E02 audit baseline differs")
    for key, count in (("probeCount", len(bundle["probes"])), ("sourceRecords", len(definition["sourceEvidence"])),
                       ("observationGroups", len(definition["observations"]))):
        if type(manifest[key]) is not int or manifest[key] != count:
            raise ValueError("E02 audit denominator differs: " + key)
    comparison = {"default": "strict", "native": PROFILE, "rawStrictRetained": True,
                  "inputPreservation": "exact", "coordinates": {"absTol": 1e-6, "relTol": 1e-9},
                  "geometryAndDeterminism": "independent gates", "lifecycleAcceptance": "NOT_ASSESSED"}
    if (manifest["frozenRulesSha256"] != definition["evidenceSeal"]["rulesSha256"]
            or not diff(manifest["comparison"], comparison)["passed"]
            or manifest["algorithmSourceGate"] != "unverified"):
        raise ValueError("E02 audit hides strict/profile/lifecycle boundaries")


def replay_probes(original, recaptured, lock):
    old, new = validate_probes(original, lock), validate_probes(recaptured, lock)
    if old.keys() != new.keys():
        raise ValueError("Recaptured probe denominator differs")
    differences = []
    for identity in old:
        if old[identity]["requestSha256"] != new[identity]["requestSha256"]:
            raise ValueError("Recaptured request fingerprint differs: " + identity)
        a, b = copy.deepcopy(old[identity]["observation"]), copy.deepcopy(new[identity]["observation"])
        # Host versions are provenance, not graph fields. Tool-owned error stacks
        # were already removed by the collector at its exact error-record paths.
        for observation in (a, b):
            for key in ("node", "platform", "arch"):
                observation["engine"].pop(key, None)
        compared = diff(a, b)
        if not compared["passed"]:
            differences.append({"probe": identity, **compared})
    return {"passed": not differences, "probeCount": len(old), "differences": differences,
            "limitation": "Official FakeWorker probe replay; no native Python behavior accepted."}


def check(root: Path = ROOT, *, with_upstream=False, replay=None):
    errors = []
    controls = None
    try:
        errors.extend(check_plan(root))
        lock = load(root / "UPSTREAM.json")
        definition = load(root / "references/native-contract.json")
        bundle = load(root / "references/e02-contract-probes.json")
        probes = validate_probes(bundle, lock)
        validate_definition(definition, probes, lock)
        seal = definition["evidenceSeal"]
        if (seal["probeManifestPath"] != "references/e02-contract-probes.json"
                or seal["probeManifestSha256"] != sha256(root / seal["probeManifestPath"])
                or seal["probeTool"] != bundle["tool"] or seal["probeCount"] != len(probes)
                or seal["allRequestBytesAndRawObservationHashesChecked"] is not True):
            errors.append("Contract final evidence seal differs from probe corpus")
        manifest = load(root / "references/e02-audit.json")
        validate_manifest(manifest, definition, bundle)
        required = {"references/native-contract.json", "references/e02-contract-probes.json", definition["decisionDocument"]}
        if not required <= manifest["filesSha256"].keys():
            errors.append("E02 evidence denominator differs")
        for path, digest in manifest["filesSha256"].items():
            if sha256(contained(root, path)) != digest:
                errors.append("E02 artifact SHA256 mismatch: " + path)
        if sha256(contained(root, bundle["tool"]["path"])) != bundle["tool"]["sha256"]:
            errors.append("Probe collector source fingerprint differs")
        if manifest["probeIds"] != [probe["id"] for probe in bundle["probes"]]:
            errors.append("E02 probe IDs/order differ from sealed inventory")
        if manifest["requestSha256ByProbe"] != {p["id"]: p["requestSha256"] for p in bundle["probes"]}:
            errors.append("E02 requests differ from sealed probe inventory")
        for comparator in (compare_observations, compare_captures):
            if inspect.signature(comparator).parameters["profile"].default != "strict":
                errors.append("Strict must remain the default comparison")
        controls = profile_smoke(root)
        known = {**lock["sourceSha256"], **lock["distribution"]["sha256Files"]}
        indexed = load(root / "references/assertion-inventory.json")
        known.update({source["path"]: source["sha256"] for source in indexed["sources"]})
        for source in definition["sourceEvidence"] + bundle["sources"]:
            if source["commit"] != lock["javascript"]["commit"] or known.get(source["path"]) != source["sha256"]:
                errors.append("Contract source identity differs: " + source["sourceId"])
        if with_upstream:
            import upstream
            upstream.verify_source(root / ".local/upstream-elkjs", lock)
            upstream.verify_package(root / ".local/npm-elkjs/package", lock)
            for source in definition["sourceEvidence"]:
                raw = upstream.git(root / ".local/upstream-elkjs", "show", source["commit"] + ":" + source["path"])
                if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                    errors.append("Canonical contract source SHA differs: " + source["sourceId"])
        if replay is not None:
            result = replay_probes(bundle, load(replay), lock)
            if not result["passed"]:
                errors.append("Official probe behavior replay differs")
        else:
            result = None
    except (ValueError, KeyError, TypeError, OSError) as error:
        errors.append(str(error))
        result = None
    return {"schema": "py-elk-e02-validation/v1", "status": "E02_CONTRACT_VALIDATED" if not errors else "FAIL",
            "errors": errors, "controls": controls, "replay": result, "pythonAlgorithmsVerified": 0,
            "limitation": "Contract/profile tooling validation only; no native API, algorithm, lifecycle or package-release acceptance."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true")
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = check(with_upstream=args.with_upstream, replay=args.replay)
    if args.out:
        write(args.out, report)
    print(json.dumps({"status": report["status"], "errors": report["errors"], "pythonAlgorithmsVerified": 0}, indent=2))
    raise SystemExit(bool(report["errors"]))
