"""Audit E04's versioned installed evidence and current experimental declarations.

This offline check validates receipts, fingerprints and bounded claims. It does
not run layout, reinstall a wheel, authenticate historical command output, or
automatically prove mathematical equivalence. The evidence describes E04's
completed slice; a later scope/implementation needs its own renewed evidence.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path

from layout_checks import ROOT, contained, load, sha256, validate_json, write
from validate_e04_source_bindings import DOCUMENTS, validate_approved_evidence

AUDIT = "references/e04-runtime-audit.json"
INSTALLED = "references/e04-installed-check.json"
SCOPE = "docs/decisions/0003-e04-generated-source-slice.md"
SUITE = "tests/fixtures/suites/E04/cases.json"
SELECTION = "tests/fixtures/suites/E04/selection.json"
NUMERIC = "references/e04-numeric-regressions.json"
POLICY = "references/e04-determinism-policy.json"
APPROVALS = "references/e04-component-approvals.json"
REQUIRED_FILES = {APPROVALS, SCOPE, SUITE, SELECTION, INSTALLED, NUMERIC, POLICY}
BASELINE = {"version": "0.12.1", "commit": "624ae90aa37110033a8af59c5ccbb292708b4317"}
BUNDLED = "b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7"
WORKER = "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86"
SCOPE_ID = "E04-ADR0003-revision4"
CLAIMS = {"nativeLayoutImplemented": True, "experimentalSliceAvailable": True,
          "publicLayoutApiAccepted": False, "fullAlgorithmAccepted": False,
          "lifecycleAccepted": False, "concurrencyAccepted": False,
          "cancellationAccepted": False, "releaseAccepted": False, "packagePublished": False}
DENOMINATORS = {"algorithms": 12, "options": 243, "categories": 8, "masterCases": 25,
                "selectedMasterCases": 5, "excludedMasterCases": 20, "projectVariants": 16,
                "sliceCases": 21, "numericPositiveCases": 12, "numericNegativeCases": 1}
SCOPE_VALUE = {"id": SCOPE_ID, "document": SCOPE, "topology": "flat-connected-directed-simple-path",
               "minimumNodes": 0, "maximumNodes": 4, "directions": ["RIGHT", "UNDEFINED"],
               "edgeRouting": "ORTHOGONAL", "numericMaximum": 1_000_000, "nonzeroSigned32Seed": True,
               "explicitPaddingType": "string", "renewSourceApprovalBeforeExpansion": True}
API = {"ELK.constructor", "ELK.layout", "ELK.knownLayoutAlgorithms", "ELK.knownLayoutOptions",
       "ELK.knownLayoutCategories", "ELK.terminateWorker"}
EXPERIMENTAL_API = {"ELK.constructor", "ELK.layout", "ELK.terminateWorker"}
CROSS_CUTTING = {
    "json-schema-and-id-identity", "primitive-extended-and-hyperedges", "options-defaults-aliases-and-scopes",
    "numeric-and-random-semantics", "input-preservation-and-custom-fields", "ports-and-node-sizing",
    "labels-and-given-measurements", "hierarchy-and-coordinate-systems", "routing-and-sections",
    "connected-components-and-packing", "async-concurrency-cancellation-lifecycle", "errors-logging-and-timing",
    "metadata-and-registration", "offline-packaging-and-platforms", "py-mermaid-integration",
}
COMMANDS = ["suite", "installed-wheel", "candidate-command", "reference", "candidate", "compare"]
HASH = re.compile(r"[0-9a-f]{64}\Z")
HISTORICAL_MATERIAL = "references/history/E04/material.json"
HISTORICAL_WHEEL = "references/history/E04/py_elk-0.0.1a0-py3-none-any.whl"
HISTORICAL_WHEEL_SHA = "7ebf9e042028bb4fdc3e73270066d398c285a1af2c5b2cb3cc7a39c5e30d95f7"
HISTORICAL_DECLARATIONS = {
    "UPSTREAM.json": "91856f51262e99679a0cae50d8c8a6ccd302a7daa1c94b5ca96b14afc5c96aa1",
    "docs/compatibility.json": "c4a8ec0c02ffd655f01a46abd2e04abf71320553f90f206ceaf05524d7980f69",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value, expected, message):
    """JSON equality with exact scalar types: false must never stand for zero."""
    require(type(value) is type(expected), message)
    if type(expected) is dict:
        require(set(value) == set(expected), message)
        for key in expected:
            exact(value[key], expected[key], message)
    elif type(expected) is list:
        require(len(value) == len(expected), message)
        for left, right in zip(value, expected):
            exact(left, right, message)
    else:
        require(value == expected, message)


def digest(value):
    require(type(value) is str and HASH.fullmatch(value), "Invalid SHA256")


def embedded_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate embedded JSON key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError("Nonfinite embedded JSON")))
    validate_json(value)
    return value


def indexed(rows, message):
    require(type(rows) is list and all(type(row) is dict and type(row.get("id")) is str for row in rows), message)
    result = {row["id"]: row for row in rows}
    require(len(result) == len(rows), message)
    return result


def no_full_acceptance(value):
    forbidden = {"fullAlgorithmAccepted", "publicLayoutApiAccepted", "publicApiAccepted", "lifecycleAccepted",
                 "concurrencyAccepted", "cancellationAccepted", "releaseAccepted", "packagePublished"}
    if type(value) is dict:
        for key, child in value.items():
            if key in forbidden:
                exact(child, False, "Complete capability or publication claim differs: " + key)
            if key == "pythonAlgorithmsVerified":
                exact(child, 0, "Full algorithm count must remain integer zero")
            no_full_acceptance(child)
    elif type(value) is list:
        for child in value:
            no_full_acceptance(child)


def validate_audit(audit, root):
    require(audit["schema"] == "py-elk-e04-runtime-audit/v1" and audit["iteration"] == "E04"
            and audit["status"] == "E04_EXPERIMENTAL_SLICE_VERIFIED", "E04 audit identity/status differs")
    exact(audit["baseline"], BASELINE, "E04 baseline differs")
    exact(audit["scope"], SCOPE_VALUE, "E04 bounded scope differs")
    exact(audit["runtimeClaims"], CLAIMS, "E04 runtime claims differ")
    exact(audit["coverageDenominators"], DENOMINATORS, "E04 coverage denominator differs")
    exact(audit["pythonAlgorithmsVerified"], 0, "Full algorithm count must remain integer zero")
    exact(audit["availableExperimentalAlgorithms"], ["org.eclipse.elk.layered"], "Experimental algorithm differs")
    require(audit["installedEvidence"] == INSTALLED and audit["algorithmSourceGate"] ==
            "verified-for-guarded-generated-source-slice-only", "E04 source/evidence category differs")
    require(set(audit["filesSha256"]) == REQUIRED_FILES, "E04 evidence file denominator differs")
    for path, fingerprint in audit["filesSha256"].items():
        digest(fingerprint)
        require(sha256(contained(root, path)) == fingerprint, "E04 versioned evidence SHA differs: " + path)
    no_full_acceptance(audit)


def validate_claims(lock, ledger, audit_sha, root, *, audit_path=AUDIT, scope_id=SCOPE_ID, case_count=21):
    require(lock["javascript"]["version"] == BASELINE["version"] and
            lock["javascript"]["commit"] == BASELINE["commit"], "Locked baseline differs")
    require(lock["javascript"]["repository"] == "https://github.com/kieler/elkjs" and
            lock["javascript"]["npmPackage"] == "elkjs" and
            lock["distribution"]["gitHead"] == BASELINE["commit"] and
            lock["metadataCapture"]["entrypoint"] == "lib/elk.bundled.js", "Locked source roles differ")
    require(lock["distribution"]["sha256Files"]["lib/elk.bundled.js"] == BUNDLED and
            lock["distribution"]["sha256Files"]["lib/elk-worker.js"] == WORKER,
            "Locked bundled/worker fingerprints differ")
    require(ledger["schema"] == "py-elk-compatibility/v1" and ledger["upstreamVersion"] == BASELINE["version"]
            and ledger["upstreamCommit"] == BASELINE["commit"], "Compatibility baseline differs")
    no_full_acceptance(lock)
    no_full_acceptance(ledger)
    python = lock["python"]
    exact(python["runtimeImplemented"], True, "Native experimental runtime must be explicit")
    exact(python["implementedAlgorithms"], [], "Complete implemented algorithms must remain empty")
    exact(python["fullAlgorithmAccepted"], False, "Full algorithm acceptance differs")
    exact(python["packagePublished"], False, "Publication acceptance differs")
    evidence = {"path": audit_path, "sha256": audit_sha}
    exact(python["experimentalAlgorithms"], [{"id": "org.eclipse.elk.layered", "scope": scope_id, "evidence": evidence}],
          "UPSTREAM experimental declaration differs")
    require(python["runtimeEvidence"] == audit_path, "Runtime evidence path differs")
    exact(lock["metadataCapture"]["counts"], {"algorithms": 12, "options": 243, "categories": 8}, "Catalogue count differs")
    exact(lock["referenceFixtures"]["caseCount"], 25, "Master fixture denominator differs")
    exact(lock["releasePlan"]["currentScaffoldIsPublishable"], False, "Scaffold is not a formal release")
    for kind, count in (("algorithms", 12), ("options", 243), ("categories", 8)):
        path = "references/metadata/" + kind + ".json"
        require(sha256(contained(root, path)) == lock["metadataCapture"]["files"][path], "Captured catalogue SHA differs")
        official = indexed(load(root / path), "Invalid official catalogue IDs")
        rows = indexed(ledger[kind], "Invalid compatibility catalogue IDs")
        require(len(rows) == count and set(rows) == set(official), "Compatibility catalogue denominator differs: " + kind)
        for identity, row in rows.items():
            experimental = kind == "algorithms" and identity == "org.eclipse.elk.layered"
            keys = {"id", "status", "evidence"} | ({"api", "semantics", "coordinates"} if kind == "algorithms" else set())
            require(set(row) == keys | ({"scope"} if experimental else set()), "Unexpected catalogue acceptance field")
            require(row["status"] == ("experimental" if experimental else "inventoried" if kind == "algorithms" else "planned"),
                    "Complete catalogue acceptance must remain planned")
            exact(row["evidence"], [evidence] if experimental else [], "Catalogue evidence category differs")
            if kind == "algorithms":
                require(all(row[name] == "planned" for name in ("api", "semantics", "coordinates")), "Full algorithm stages differ")
            if experimental:
                require(row["scope"] == scope_id, "Layered scope differs")
    apis = indexed(ledger["api"], "Invalid API IDs")
    require(set(apis) == API, "Full API denominator differs")
    for identity, row in apis.items():
        experimental = identity in EXPERIMENTAL_API
        require(set(row) == {"id", "status", "evidence"} | ({"scope"} if experimental else set()), "Unexpected API acceptance field")
        require(row["status"] == ("experimental" if experimental else "planned"), "Complete public API is not accepted")
        exact(row["evidence"], [evidence] if experimental else [], "API evidence category differs")
        if experimental:
            require(row["scope"] == scope_id, "API scope differs")
    cross_cutting = indexed(ledger["crossCutting"], "Invalid cross-cutting IDs")
    require(set(cross_cutting) == CROSS_CUTTING
            and all(set(row) == {"id", "status", "evidence"} and row["status"] == "planned" and row["evidence"] == []
                    for row in cross_cutting.values()),
            "Cross-cutting lifecycle/release acceptance differs")
    exact(ledger["experimentalSlice"], {"id": scope_id, "algorithm": "org.eclipse.elk.layered", "casesVerified": case_count,
          "fullAlgorithmAccepted": False, "publicApiAccepted": False, "lifecycleAccepted": False, "evidence": [evidence]},
          "Ledger experimental slice differs")


def suite_requests(root, *, suite_path=SUITE, selection_path=SELECTION, selected_count=5,
                   excluded_count=20, variant_count=16, case_count=21):
    suite = load(root / suite_path)
    require(suite["schema"] == "py-elk-validation-cases/v1", "Suite schema differs")
    rows = indexed(suite["cases"], "Invalid E04 suite IDs")
    require(len(rows) == case_count, "Suite must keep all" + str(case_count) + " cases")
    selection = load(root / selection_path)
    exact(selection["master"]["caseCount"], 25, "Master denominator differs")
    exact(selection["selectedMasterCases"], selected_count, "Selected master denominator differs")
    exact(selection["excludedMasterCases"], excluded_count, "Excluded master denominator differs")
    exact(selection["projectVariantCount"], variant_count, "Variant denominator differs")
    exact(selection["suiteCaseCount"], case_count, "Selected slice denominator differs")
    masters = indexed(selection["masterCases"], "Invalid master selection IDs")
    variants = indexed(selection["projectVariants"], "Invalid project variant IDs")
    require(len(masters) == 25 and len(variants) == variant_count, "Selection record denominator differs")
    master_path = contained(root, selection["master"]["path"])
    require(sha256(master_path) == selection["master"]["sha256"] and
            set(indexed(load(master_path)["cases"], "Invalid original master IDs")) == set(masters),
            "Original master request denominator differs")
    selected = {key: row for key, row in masters.items() if row["included"] is True}
    require(len(selected) == selected_count and set(rows) == set(selected) | set(variants) and not set(selected) & set(variants),
            "Selection and suite IDs differ")
    requests = {}
    for identity, row in rows.items():
        path = contained((root / suite_path).parent, row["request"])
        fingerprint = sha256(path)
        selected_sha = selected[identity]["originalRequestSha256"] if identity in selected else variants[identity]["requestSha256"]
        require(fingerprint == selected_sha, "Selected original request SHA differs")
        requests[identity] = (fingerprint, load(path))
    return requests


def effective_seed(request):
    constructor, args, graph = request["constructor"], request["layoutArguments"], request["graph"]
    options = args["layoutOptions"] if "layoutOptions" in args else constructor.get("defaultLayoutOptions", {})
    seed, source = 1, "fixed-source-default"
    for scope in (options, graph.get("layoutOptions", {})):
        require(type(scope) is dict, "Invalid selected seed option container")
        keys = [key for key in ("randomSeed", "elk.randomSeed", "org.eclipse.elk.randomSeed") if key in scope]
        require(len(keys) <= 1, "Ambiguous effective seed aliases")
        if keys:
            seed, source = scope[keys[0]], "explicit-request"
            if type(seed) is str and re.fullmatch(r"[+-]?\d+", seed):
                seed = int(seed)
            # E03 parses each selected scope before applying local overrides.
            # Zero is a valid configured value here and may be overridden;
            # false/null/invalid values are never a default-seed fallback.
            require(type(seed) is int and -(2**31) <= seed < 2**31, "Invalid selected seed value")
    require(type(seed) is int and -(2**31) <= seed < 2**31 and seed != 0, "Invalid or nondeterministic effective seed")
    return seed, source


def historical_path(value, cwd=""):
    """Lexical identity only: never resolve historical C: paths on this host."""
    require(type(value) is str and value and "\x00" not in value, "Invalid historical path")
    value = value.replace("\\", "/")
    if not value.startswith("/") and not re.match(r"^[A-Za-z]:/", value):
        value = posixpath.join(cwd.replace("\\", "/"), value)
    normalized = posixpath.normpath(value)
    return normalized.casefold() if re.match(r"^[A-Za-z]:/", normalized) else normalized


def command_options(row, script, action=None, *, isolated=False):
    argv, cwd = row["argv"], row["cwd"]
    offset = 2 if isolated else 1
    require(len(argv) > offset and historical_path(argv[offset], cwd) == historical_path(script, cwd),
            "Historical command collector entrypoint differs: " + row["name"])
    if isolated:
        require(argv[1] == "-I", "Historical installed interpreter is not isolated")
    offset += 1
    if action is not None:
        require(len(argv) > offset and argv[offset] == action, "Historical command action differs: " + row["name"])
        offset += 1
    pairs = argv[offset:]
    require(len(pairs) % 2 == 0, "Historical command flags are not pairs")
    options = {}
    for flag, value in zip(pairs[::2], pairs[1::2]):
        require(flag.startswith("--") and flag not in options and value and not value.startswith("--"),
                "Historical command has ambiguous flags")
        options[flag] = value
    return options


def validate_command_roles(commands, summary, *, suite_path=SUITE, builder="scripts/build_slice_suite.py"):
    """Check the six recorded producer roles and their same-run relationships.

    These argv strings are receipts, not executable instructions. Lexical checks
    work on a fresh Linux checkout with the unchanged historical Windows paths.
    """
    suite, installed, adapter, reference, candidate, compare = commands
    host = historical_path(suite["argv"][0], suite["cwd"])
    require(all(historical_path(row["cwd"]) == historical_path(suite["cwd"]) for row in commands),
            "Historical command working directories differ")
    require(all(historical_path(row["argv"][0], row["cwd"]) == host for row in (adapter, reference, candidate, compare)),
            "Historical host interpreter roles differ")
    selected = command_options(suite, builder, "check")
    require(set(selected) == {"--suite"} and historical_path(selected["--suite"], suite["cwd"]) ==
            historical_path(posixpath.dirname(suite_path), suite["cwd"]), "Historical suite selection differs")
    # The original installed-wheel invocation has one positional wheel argument.
    argv = installed["argv"]
    require(len(argv) == 6 and argv[1] == "-I" and
            historical_path(argv[2], installed["cwd"]) == historical_path("scripts/verify_installed_wheel.py", installed["cwd"])
            and argv[3].endswith(".whl") and argv[4] == "--out", "Historical installed-wheel role differs")
    generated = command_options(adapter, "scripts/validate_layout.py", "candidate-command")
    require(set(generated) == {"--python", "--out"} and historical_path(generated["--python"], adapter["cwd"]) ==
            historical_path(installed["argv"][0], installed["cwd"]), "Historical candidate interpreter differs")
    ref = command_options(reference, "scripts/validate_layout.py", "reference")
    native = command_options(candidate, "scripts/validate_layout.py", "candidate")
    require(set(ref) == {"--cases", "--package", "--repeat", "--out"} and
            set(native) == {"--cases", "--command-json", "--repeat", "--out"}, "Historical capture flags differ")
    for row, options in ((reference, ref), (candidate, native)):
        require(historical_path(options["--cases"], row["cwd"]) == historical_path(suite_path, row["cwd"]),
                "Historical capture does not use the same " + ("E04" if suite_path == SUITE else "E05") + " suite")
        require(options["--repeat"] == str(summary["repeat"]), "Historical capture repeats differ")
    require(historical_path(native["--command-json"], candidate["cwd"]) == historical_path(generated["--out"], adapter["cwd"]),
            "Historical candidate capture did not use the generated adapter")
    compared = command_options(compare, "scripts/validate_layout.py", "compare")
    require(set(compared) == {"--profile", "--determinism-policy", "--reference", "--candidate", "--out"} and
            compared["--profile"] == summary["profile"] and compared["--determinism-policy"] == summary["determinismPolicy"],
            "Historical compare role/policy differs")
    require(historical_path(compared["--reference"], compare["cwd"]) == historical_path(ref["--out"], reference["cwd"]) and
            historical_path(compared["--candidate"], compare["cwd"]) == historical_path(native["--out"], candidate["cwd"]),
            "Historical comparison does not consume the recorded captures")


def historical_material(root, *, iteration="E04", material_path=HISTORICAL_MATERIAL,
                        wheel_path=HISTORICAL_WHEEL, wheel_sha=HISTORICAL_WHEEL_SHA,
                        declarations_sha=HISTORICAL_DECLARATIONS):
    """Read an explicitly pinned frozen package without importing or executing it.

    Defaults preserve the E04 identity and all original semantic checks. Later
    iterations must supply their own fixed identities, not trust editable
    fingerprints from the material document itself.
    """
    material = load(root / material_path)
    require(material["schema"] == "py-elk-historical-runtime-material/v1" and material["iteration"] == iteration,
            "Historical material identity differs")
    require(set(material["declarations"]) == set(declarations_sha), "Historical declaration denominator differs")
    declarations = {}
    for path, expected in declarations_sha.items():
        receipt = material["declarations"][path]
        raw = base64.b64decode(receipt["bytesBase64"], validate=True)
        require(receipt["sha256"] == expected == hashlib.sha256(raw).hexdigest(), "Historical declaration bytes differ")
        declarations[path] = embedded_json(raw)
    exact(material["wheel"], {"path": wheel_path, "sha256": wheel_sha}, "Historical wheel identity differs")
    wheel = contained(root, wheel_path)
    require(sha256(wheel) == wheel_sha, "Historical wheel bytes differ")
    package = {}
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate historical wheel member")
        for name in names:
            if name.startswith("pyelk/") and not name.endswith("/"):
                relative = name[len("pyelk/"):]
                require(relative and not any(part in ("", ".", "..") for part in relative.split("/"))
                        and "\\" not in relative, "Unsafe historical wheel package member")
                package[relative] = archive.read(name)
    require(package, "Historical wheel package is empty")
    return declarations, package


def validate_installed(summary, requests, root, *, package_bytes=None, iteration="E04", suite_path=SUITE,
                       case_count=21, builder="scripts/build_slice_suite.py", additional_licenses=()):
    require(summary["schema"] == "py-elk-" + iteration.lower() + "-installed-evidence/v1" and summary["iteration"] == iteration
            and summary["status"] == iteration + "_INSTALLED_SLICE_PASS", "Installed evidence identity/status differs")
    for key in ("passed", "historicalEvidenceOnly", "isolatedInterpreter"):
        exact(summary[key], True, "Installed evidence flag differs: " + key)
    no_full_acceptance(summary)
    exact(summary["pythonAlgorithmsVerified"], 0, "Full algorithm count must remain integer zero")
    exact(summary["fullAlgorithmAccepted"], False, "Installed evidence is not full algorithm acceptance")
    exact(summary["packagePublished"], False, "Installed evidence is not publication acceptance")
    require(summary["profile"] == "native-basic-layered-v1" and summary["determinismPolicy"] == "elkjs-0.12.1-default-seed-v1",
            "Installed profile/policy differs")
    exact(summary["tolerance"], {"absolute": 1e-6, "relative": 1e-9, "appliesTo": "geometry numeric paths only"}, "Tolerance differs")
    exact(summary["caseCount"], case_count, "Installed case denominator differs")
    repeat = summary["repeat"]
    minimum_repeat = 2 if iteration == "E04" else 3
    require(type(repeat) is int and repeat >= minimum_repeat, "Installed repeat count must be an integer >=" + str(minimum_repeat))
    require(summary["suiteSha256"] == sha256(root / suite_path), "Installed suite SHA differs")
    digest(summary["wheelSha256"])
    require(type(summary["wheelVersion"]) is str and summary["wheelVersion"], "Missing wheel version")
    commands = summary["commands"]
    expected_commands = COMMANDS if iteration == "E04" else ["suite", "source-approval", *COMMANDS[1:]]
    require(type(commands) is list and [row["name"] for row in commands] == expected_commands, "Installed command denominator/order differs")
    for row in commands:
        exact(row["exitCode"], 0, "Historical command failed")
        exact(row["timedOut"], False, "Historical command timed out")
        require(type(row["argv"]) is list and row["argv"] and all(type(arg) is str for arg in row["argv"]), "Invalid historical argv")
        require(type(row["cwd"]) is str and row["cwd"], "Missing historical working directory")
        for stream in ("stdoutSha256", "stderrSha256"):
            digest(row[stream])
        expected_environment = "EMPTY_PATH_NO_PYTHON_OVERRIDES" if row["name"] in ("installed-wheel", "candidate") else "inherited"
        require(row["environmentPolicy"] == expected_environment, "Historical candidate environment is not isolated")
        if row["name"] == "installed-wheel":
            require("-I" in row["argv"], "Installed verification did not use an isolated interpreter")
        if row["name"] in ("reference", "candidate"):
            require(row["argv"][row["argv"].index("--repeat") + 1] == str(repeat), "Command repeat count differs")
        if row["name"] == "compare":
            for flag, expected in (("--profile", summary["profile"]), ("--determinism-policy", summary["determinismPolicy"])):
                require(row["argv"][row["argv"].index(flag) + 1] == expected, "Historical comparison policy differs")
    if iteration != "E04":
        approval = commands[1]
        require(len(approval["argv"]) == 3 and approval["argv"][2] == "--require-approved" and
                historical_path(approval["argv"][1], approval["cwd"]) ==
                historical_path("scripts/validate_" + iteration.lower() + "_source_bindings.py", approval["cwd"]), "Expanded source approval command differs")
        require(historical_path(approval["cwd"]) == historical_path(commands[0]["cwd"]) and
                historical_path(approval["argv"][0], approval["cwd"]) ==
                historical_path(commands[0]["argv"][0], commands[0]["cwd"]), "Source approval producer differs")
    validate_command_roles([row for row in commands if row["name"] != "source-approval"], summary,
                           suite_path=suite_path, builder=builder)
    cases = indexed(summary["cases"], "Invalid installed case IDs")
    require(len(requests) == case_count and set(cases) == set(requests), "Installed case IDs do not cover the same requests")
    for identity, case in cases.items():
        fingerprint, request = requests[identity]
        require(case["requestSha256"] == fingerprint, "Installed request SHA differs")
        exact(case["repetitionsCompared"], repeat, "Installed repetitions differ")
        for key in ("passed", "nativePublicExact", "nativePublicTolerance", "candidateGeometry", "referenceGeometry", "candidateInputPreserved"):
            exact(case[key], True, "Installed case check failed: " + key)
        exact(case["strictPassed"], False, "Raw JS strict differences must remain visible")
        seed, source = effective_seed(request)
        for key in ("referenceDeterminism", "candidateDeterminism"):
            exact(case[key], {"passed": True, "status": "CHECKED", "repeats": repeat, "seed": seed, "seedSource": source},
                  "Installed deterministic context differs")
    fingerprints = summary["packageFilesSha256"]
    require(type(fingerprints) is dict and fingerprints, "Missing actual installed package fingerprints")
    package = root / "src/pyelk"
    required = ({p.relative_to(package).as_posix() for p in package.rglob("*.py") if "__pycache__" not in p.parts}
                if package_bytes is None else {name for name in package_bytes if name.endswith(".py")})
    required |= {"_licenses/NOTICE.md", "_licenses/elkjs-LICENSE.md", *additional_licenses}
    required |= ({p.relative_to(package).as_posix() for p in (package / "_licenses").rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts}
                 if package_bytes is None else {name for name in package_bytes if name.startswith("_licenses/")})
    require(set(fingerprints) in (required, required | {"py.typed"}), "Installed Python/license file denominator differs")
    for name, fingerprint in fingerprints.items():
        digest(fingerprint)
        actual = (sha256(contained(package, name)) if package_bytes is None
                  else hashlib.sha256(package_bytes[name]).hexdigest())
        require(actual == fingerprint, "Current package bytes differ from the installed evidence: " + name)
    original = summary["originalFilesSha256"]
    require(set(original) == {"report.json", "comparison.json", "installed-wheel.json", "reference/index.json", "candidate/index.json"},
            "Original historical receipt denominator differs")
    for fingerprint in original.values():
        digest(fingerprint)
    require(type(summary["sourceSha256AtExecution"]) is dict and summary["sourceSha256AtExecution"], "Missing historical source identity")
    for path, fingerprint in summary["sourceSha256AtExecution"].items():
        digest(fingerprint)
        if path.startswith("src/pyelk/"):
            require(fingerprints.get(path[len("src/pyelk/"):]) == fingerprint, "Historical and installed production identities differ")


def validate_numeric(pack):
    no_full_acceptance(pack)
    require(pack["schema"] == "py-elk-e04-numeric-regressions/v1", "Numeric receipt schema differs")
    exact(pack["counts"], {"positive": 12, "domainNegative": 1, "total": 13}, "Numeric denominator differs")
    require(pack["baseline"]["version"] == BASELINE["version"] and pack["baseline"]["commit"] == BASELINE["commit"]
            and pack["baseline"]["workerSha256"] == WORKER and pack["baseline"]["bundledSha256"] == BUNDLED, "Numeric source identity differs")
    cases = indexed(pack["cases"], "Invalid numeric IDs")
    require(len(cases) == 13 and sum(c["kind"] == "positive" for c in cases.values()) == 12
            and sum(c["kind"] == "domain-negative" for c in cases.values()) == 1, "Numeric case denominator differs")
    for case in cases.values():
        request = base64.b64decode(case["requestBytesBase64"], validate=True)
        raw = base64.b64decode(case["rawObservationBytesBase64"], validate=True)
        require(hashlib.sha256(request).hexdigest() == case["requestSha256"] and
                hashlib.sha256(raw).hexdigest() == case["rawObservationSha256"], "Embedded numeric bytes SHA differs")
        request_document, observation = embedded_json(request), embedded_json(raw)
        no_full_acceptance(observation)
        require(request_document["schema"] == "py-elk-layout-request/v1" and
                observation["schema"] == "py-elk-layout-observation/v1", "Numeric embedded schema differs")
        require(observation["requestSha256"] == case["requestSha256"], "Numeric observation request identity differs")
        exact(observation["engine"], case["engine"], "Numeric engine receipt differs")
        require(observation["engine"]["name"] == "elkjs" and observation["engine"]["version"] == BASELINE["version"]
                and observation["engine"]["entrypoint"] == "lib/elk.bundled.js"
                and observation["engine"]["entrypointSha256"] == BUNDLED, "Numeric oracle baseline differs")
        expected = "returned" if case["kind"] == "positive" else "threw"
        require(observation["outcome"] == case["expectedReferenceOutcome"] == expected, "Numeric reference outcome differs")
        expectation = "public-contract-exact-and-independent-geometry" if case["kind"] == "positive" else "reject-outside-E04-domain"
        require(case["nativeExpectation"] == expectation, "Numeric native acceptance category differs")
        if case["kind"] == "domain-negative":
            require(type(request_document["graph"]["layoutOptions"]["elk.padding"]) is dict, "Numeric negative padding domain differs")
            exact(observation["error"], {"name": "Error", "message": "java.lang.Error: Severe implementation error in the Json to ElkGraph importer."},
                  "Actual padding importer error differs")
        exact(case["capture"]["exitCode"], 0, "Numeric capture command failed")
        exact(observation["termination"], {"outcome": "threw", "name": "TypeError", "message": "this.worker.terminate is not a function"},
              "Actual FakeWorker close error must remain archived")


def validate_seed_policy(root):
    policy = load(root / POLICY)
    require(policy["schema"] == "py-elk-determinism-policy/v1" and policy["id"] == "elkjs-0.12.1-default-seed-v1"
            and policy["status"] == "source-reviewed", "Default seed policy identity differs")
    exact(policy["defaultSeed"], 1, "Source default seed differs")
    exact(policy["baseline"], {**BASELINE, "entrypointSha256": BUNDLED}, "Default seed baseline differs")
    source = policy["sourceEvidence"]
    require(source["path"] == "references/e03-option-sources.json" and source["optionId"] == "org.eclipse.elk.randomSeed"
            and source["sha256"] == sha256(contained(root, source["path"])), "Default seed source receipt differs")
    source_document = load(root / source["path"])
    exact(source_document["baseline"], BASELINE, "Default seed source baseline differs")
    source_options = indexed(source_document["options"], "Duplicate/invalid default seed option IDs")
    seed_option = source_options[source["optionId"]]
    exact(seed_option["declaredDefault"], 1, "Referenced source declared seed default differs")
    require(seed_option["alias"] == "elk.randomSeed" and seed_option["metadataType"] == "INT" and
            seed_option["sourceIds"] == ["elk-worker", "official-option-catalogue"], "Default seed source role differs")


def check(root=ROOT, *, historical=False):
    root = Path(root)
    errors = []
    try:
        audit = load(root / AUDIT)
        validate_audit(audit, root)
        package_bytes = None
        if historical:
            declarations, package_bytes = historical_material(root)
            lock, ledger = declarations["UPSTREAM.json"], declarations["docs/compatibility.json"]
        else:
            lock, ledger = load(root / "UPSTREAM.json"), load(root / "docs/compatibility.json")
        validate_claims(lock, ledger, sha256(root / AUDIT), root)
        approvals = load(root / APPROVALS)
        require(approvals["globalAlgorithmSourceGate"] == "verified" and approvals["scopeDocument"] == SCOPE
                and approvals["scopeDocumentSha256"] == sha256(root / SCOPE), "Source approval is not bound to this scope")
        validate_approved_evidence(root, {lane: load(root / path) for lane, path in DOCUMENTS.items()}, approvals)
        requests = suite_requests(root)
        validate_seed_policy(root)
        installed = load(root / INSTALLED)
        require(installed["wheelVersion"] == lock["python"]["scaffoldVersion"], "Installed wheel/declaration version differs")
        if historical:
            require(installed["wheelSha256"] == HISTORICAL_WHEEL_SHA, "Historical installed wheel receipt differs")
        validate_installed(installed, requests, root, package_bytes=package_bytes)
        validate_numeric(load(root / NUMERIC))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, zipfile.BadZipFile) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e04-runtime-validation/v1", "status": "E04_RUNTIME_EVIDENCE_VALIDATED" if not errors else "FAIL",
            "errors": errors, "historicalInstalledEvidenceValidated": not errors, "runtimeReexecuted": False,
            "mathematicalEquivalenceAutomaticallyProved": False, "ignoredRunFilesRequired": False,
            "historicalWheelAuthenticated": False,
            "mode": "historical-E04" if historical else "current-E04",
            "currentPackageBytesValidated": not errors and not historical,
            "historicalPackageBytesValidated": not errors and historical,
            "pythonAlgorithmsVerified": 0, "fullAlgorithmAccepted": False, "packagePublished": False,
            "limitation": "Offline receipt/claim integrity only. Without the original wheel/logs this check cannot independently authenticate historical wheel hashes or command execution, even when rebound receipts are self-consistent. The versioned21-case E04 installed experiment is not a full algorithm/API/lifecycle/release acceptance or an automatic equivalence proof."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--historical", action="store_true", help="Check actual archived E04 wheel/declarations, never certify current source")
    args = parser.parse_args()
    report = check(historical=args.historical)
    if args.out:
        write(args.out, report)
    print(json.dumps(report, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
