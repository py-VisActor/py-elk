"""Execute identical request bytes once per engine/repetition, within one NEW run.

Original case denominators and each case's policy remain independent. Objects
refer to actual subprocess receipts; this is deliberately not an old capture
index and is not accepted by the historical installed-evidence exporters.
"""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import tomllib
import uuid
import zipfile

from layout_checks import (ROOT, compare_observations, contained, contract, determinism,
                           geometry, input_preservation, load, sha256, validate_suite, write)
from validate_layout import run, source_hashes
from validate_e07_runtime import validate_metadata

SUITES = {name: "tests/fixtures/suites/" + name + "/cases.json" for name in ("E04", "E05", "E06", "E07")}
COUNTS = {"E04": 21, "E05": 36, "E06": 52, "E07": 72}
PROFILE = "native-basic-layered-v1"
POLICY = "elkjs-0.12.1-default-seed-v1"
OVERRIDE_VARIABLES = ("NODE_OPTIONS", "NODE_PATH", "PYTHONPATH", "PYTHONHOME")
VERSION_QUERY = "import json,platform,sys; print(json.dumps({'version':sys.version,'executable':sys.executable,'baseExecutable':sys._base_executable,'basePrefix':sys.base_prefix,'platform':platform.platform(),'isolated':bool(sys.flags.isolated)}))"


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_plan(root=ROOT):
    root = Path(root)
    suites, unique = {}, {}
    for name, relative in SUITES.items():
        path = contained(root, relative)
        suite = validate_suite(path)
        require(len(suite["cases"]) == COUNTS[name], "Suite case denominator differs: " + name)
        rows = []
        for case in suite["cases"]:
            request = contained(path.parent, case["request"])
            raw = request.read_bytes()
            fingerprint = hashlib.sha256(raw).hexdigest()
            item = {"caseId": case["id"], "definition": case,
                    "request": request.relative_to(root).as_posix(), "requestSha256": fingerprint}
            rows.append(item)
            previous = unique.setdefault(fingerprint, {"request": item["request"], "bytes": len(raw), "members": []})
            require(contained(root, previous["request"]).read_bytes() == raw, "Request hash collision")
            previous["members"].append({"suite": name, "caseId": case["id"]})
        suites[name] = {"path": relative, "sha256": sha256(path), "cases": rows}
    total = sum(len(value["cases"]) for value in suites.values())
    return {"schema": "py-elk-suite-execution-plan/v1", "suites": suites, "requests": unique,
            "caseCount": total, "uniqueRequests": len(unique),
            "duplicateRequestsPerEngineRepeat": total - len(unique),
            "profile": PROFILE, "determinismPolicy": POLICY,
            "limitation": "Execution sharing only; every original case/policy remains separately checked."}


def environments():
    reference = os.environ.copy()
    for key in OVERRIDE_VARIABLES:
        reference.pop(key, None)
    candidate = reference.copy()
    candidate["PATH"] = ""
    return {"reference": reference, "candidate": candidate}


def environment_evidence(role, env):
    """Record non-secret policy facts about the actual child environment."""
    require(role in ("reference", "candidate"), "Unknown environment role")
    require(all(key.upper() not in OVERRIDE_VARIABLES for key in env), "Execution environment overrides are forbidden")
    empty_path = env.get("PATH") == ""
    require(role != "candidate" or empty_path, "Candidate execution PATH must be empty")
    return {"schema": "py-elk-execution-environment-evidence/v1", "role": role,
            "environmentSha256": canonical_sha(env), "overridesAbsent": True,
            "candidatePathEmpty": empty_path if role == "candidate" else None}


def validate_environment(context, env=None):
    """Verify recorded policy; only actual execution compares the live env.

    A later read-only verifier has a different caller environment. Its checks
    bind the original opaque digest to evidence and all object context keys;
    they do not reconstruct or authenticate the original environment values.
    """
    role = context["role"]
    require(role in ("reference", "candidate"), "Unknown environment role")
    digest = context["environmentSha256"]
    require(type(digest) is str and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
            "Invalid recorded environment digest")
    expected = {"schema": "py-elk-execution-environment-evidence/v1", "role": role,
                "environmentSha256": digest, "overridesAbsent": True,
                "candidatePathEmpty": True if role == "candidate" else None}
    require(context.get("environmentEvidence") == expected and
            type(context["environmentEvidence"].get("overridesAbsent")) is bool and
            (role != "candidate" or type(context["environmentEvidence"].get("candidatePathEmpty")) is bool),
            "Recorded execution environment policy/digest differs")
    require(context["environmentPolicy"] == ("EMPTY_PATH_NO_PYTHON_OVERRIDES" if role == "candidate" else "NO_NODE_PYTHON_OVERRIDES"),
            "Recorded execution environment policy differs")
    if env is not None:
        require(environment_evidence(role, env) == expected, "Actual execution environment differs")


def execution_key(request_sha, context, repetition, scope=None):
    require(type(request_sha) is str and len(request_sha) == 64 and
            all(c in "0123456789abcdef" for c in request_sha), "Invalid request SHA")
    require(type(repetition) is int and repetition >= 0, "Invalid repetition index")
    require(type(context) is dict and context.get("schema") == "py-elk-execution-context/v1" and
            context.get("role") in ("reference", "candidate"), "Unknown engine context")
    mandatory = {"nonce", "identity", "argvTemplate", "environmentSha256", "environmentPolicy", "environmentEvidence", "workingDirectory", "sourceSha256", "actualExecutionRoot", "projectFilesSha256"}
    require(mandatory <= context.keys() and all(context[key] for key in mandatory), "Incomplete engine identity")
    scope = {"kind": "request"} if scope is None else scope
    require(type(scope) is dict and (scope == {"kind": "request"} or
            (set(scope) == {"kind", "suite", "caseId"} and scope["kind"] == "case" and scope["suite"] in SUITES and
             type(scope["caseId"]) is str and bool(scope["caseId"]))), "Unknown execution scope")
    return canonical_sha({"schema": "py-elk-request-execution-key/v1", "requestSha256": request_sha,
                          "contextSha256": canonical_sha(context), "repetition": repetition, "scope": scope})


def _tree_files(root):
    root = Path(root).resolve()
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            require(not path.is_symlink() and path.resolve().is_relative_to(root), "External package link")
            result[path.relative_to(root).as_posix()] = sha256(path)
    require(bool(result), "Empty package identity")
    return result


def project_identity(root=ROOT):
    root = Path(root)
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    readme = project["readme"]
    require(type(readme) is str, "Current project must declare its README file")
    readme_path = contained(root, readme)
    return {"pyproject.toml": sha256(root / "pyproject.toml"), readme_path.relative_to(root).as_posix(): sha256(readme_path)}


def current_metadata(installed, root=ROOT):
    """Bind raw wheel METADATA to current declarations, not only to itself."""
    return validate_metadata({"wheelVersion": installed["version"],
                              "distributionMetadata": installed["distributionMetadata"]}, root)


def _command(out, name, argv, env, timeout=300):
    directory = out / name
    directory.mkdir()
    record = run(argv, directory, timeout, env=env)
    require(type(record["exitCode"]) is int and record["exitCode"] == 0 and record["timedOut"] is False, "Actual process failed: " + name)
    return record


def create_contexts(out, candidate_python, wheel, package, node, envs):
    for role in ("reference", "candidate"):
        environment_evidence(role, envs[role])
    candidate_python, wheel, package = (Path(p).resolve() for p in (candidate_python, wheel, package))
    node = Path(shutil.which(str(node)) or str(node)).resolve()
    require(candidate_python.is_file() and wheel.is_file() and node.is_file() and package.is_dir(), "Missing actual engine files")
    prefix = [str(candidate_python), "-I"]
    _command(out, "candidate-identity-command", [*prefix, "-c", VERSION_QUERY], envs["candidate"])
    python_identity = load(out / "candidate-identity-command/stdout.log")
    require(python_identity["isolated"] is True, "Candidate identity is not isolated")
    _command(out, "node-identity-command", [str(node), "--version"], envs["reference"])
    node_version = (out / "node-identity-command/stdout.log").read_text(encoding="utf-8").strip()
    require(node_version.startswith("v") and len(node_version) > 1, "Node version receipt differs")
    _command(out, "installed-wheel-command", [*prefix, str(ROOT / "scripts/verify_installed_wheel.py"), str(wheel),
             "--out", str(out / "installed-wheel.json")], envs["candidate"])
    installed = load(out / "installed-wheel.json")
    require(installed["status"] == "INSTALLED_WHEEL_BYTES_MATCH" and installed["isolatedInterpreter"] is True,
            "Actual wheel installation differs")
    require(not Path(installed["modulePath"]).resolve().is_relative_to(ROOT / "src"), "Source-tree candidate is not allowed")
    current = _tree_files(ROOT / "src/pyelk")
    # Runtime package identity covers every packaged Python, notice and marker.
    required = {name: fingerprint for name, fingerprint in current.items()
                if name.endswith(".py") or name.startswith("_licenses/") or name == "py.typed"}
    require(installed["packageFilesSha256"] == required, "Installed wheel cannot certify changed current sources")
    require(installed["python"] == python_identity["version"], "Candidate version receipt differs")
    current_metadata(installed)
    lock = load(ROOT / "UPSTREAM.json")
    files = _tree_files(package)
    require(all(files.get(name) == fingerprint for name, fingerprint in lock["distribution"]["sha256Files"].items()),
            "Pinned reference package differs")
    nonce = uuid.uuid4().hex
    common = {"schema": "py-elk-execution-context/v1", "nonce": nonce,
              "sourceSha256": source_hashes(), "workingDirectory": str(ROOT),
              "actualExecutionRoot": str(out),
              "upstreamLockSha256": sha256(ROOT / "UPSTREAM.json"),
              "projectFilesSha256": project_identity(),
              "seedPolicySha256": sha256(ROOT / "references/e04-determinism-policy.json")}
    binaries = {str(candidate_python): sha256(candidate_python)}
    base_exe = Path(python_identity["baseExecutable"]).resolve()
    require(base_exe.is_file(), "Missing base interpreter identity")
    binaries[str(base_exe)] = sha256(base_exe)
    # Windows venv launchers alone do not identify their base runtime DLL.
    for path in Path(python_identity["basePrefix"]).glob("python*.dll"):
        binaries[str(path.resolve())] = sha256(path)
    identities = {
        "reference": {"name": "elkjs", "node": str(node), "nodeSha256": sha256(node), "version": node_version,
                      "queryCommandSha256": sha256(out / "node-identity-command/command.json"),
                      "package": str(package), "packageFilesSha256": files, "baseline": lock["javascript"]["version"],
                      "entrypointSha256": files["lib/elk.bundled.js"]},
        "candidate": {"name": "pyelk", "python": str(candidate_python), "pythonIdentity": python_identity,
                      "queryCommandSha256": sha256(out / "candidate-identity-command/command.json"),
                      "installedCommandSha256": sha256(out / "installed-wheel-command/command.json"),
                      "binariesSha256": binaries, "wheel": str(wheel), "wheelSha256": sha256(wheel),
                      "installedReceiptSha256": sha256(out / "installed-wheel.json"),
                      "modulePath": installed["modulePath"], "version": installed["version"],
                      "packageFilesSha256": installed["packageFilesSha256"]}}
    prefixes = {"reference": [str(node), str(ROOT / "tools/reference/capture_layout.cjs"), str(package)],
                "candidate": [*prefix, str(ROOT / "scripts/run_pyelk_candidate.py")]}
    return {role: {**common, "role": role, "identity": identities[role],
                   "argvTemplate": [*prefixes[role], "<REQUEST>", "<OBSERVATION>"],
                   "environmentSha256": canonical_sha(envs[role]),
                   "environmentEvidence": environment_evidence(role, envs[role]),
                   "environmentPolicy": "EMPTY_PATH_NO_PYTHON_OVERRIDES" if role == "candidate" else "NO_NODE_PYTHON_OVERRIDES"}
            for role in ("reference", "candidate")}


def validate_engine(observation, context, request_sha):
    contract(observation)
    require(observation["requestSha256"] == request_sha and observation["outcome"] == "returned", "Unexpected request/outcome")
    engine, identity = observation["engine"], context["identity"]
    require(engine.get("name") == identity["name"], "Observation engine role differs")
    if context["role"] == "reference":
        require(engine.get("version") == identity["baseline"] and engine.get("node") == identity["version"] and
                engine.get("entrypointSha256") == identity["entrypointSha256"], "Reference identity differs")
    else:
        require(engine.get("version") == identity["version"] and engine.get("python") == identity["pythonIdentity"]["version"] and
                Path(engine["modulePath"]).resolve() == (Path(identity["modulePath"]) / "__init__.py").resolve() and
                Path(engine["executable"]).resolve() == Path(identity["python"]).resolve(), "Candidate identity differs")
        require(engine.get("sourceSha256") == {name: value for name, value in identity["packageFilesSha256"].items() if name.endswith(".py")},
                "Candidate runtime bytes differ")


def evaluate_case(definition, request_path, reference, candidate, repeat):
    require(type(reference) is list and type(candidate) is list and type(repeat) is int and len(reference) == len(candidate) == repeat and repeat >= 3,
            "Missing independent repetitions")
    request = load(Path(request_path))
    require(definition["expectedOutcome"] == "returned" and all(o.get("outcome") == "returned" for o in reference + candidate),
            "Positive suite cannot count error outcomes")
    comparisons = [compare_observations(reference[0], row, profile=PROFILE, request=Path(request_path)) for row in candidate]
    candidate_geometry = [geometry(request, row, definition.get("geometry")) for row in candidate]
    reference_geometry = [geometry(request, row, definition.get("geometry")) for row in reference]
    preserved = [input_preservation(request, row) for row in candidate]
    rd, cd = (determinism(rows, request, policy=POLICY) for rows in (reference, candidate))
    passed = (all(row["passed"] for row in comparisons) and
              all(row["passed"] is True for row in candidate_geometry + reference_geometry) and
              all(row["preserved"] for row in preserved) and rd["passed"] and cd["passed"])
    return {"id": definition["id"], "passed": passed, "comparisons": comparisons,
            "candidateGeometry": candidate_geometry, "referenceGeometry": reference_geometry,
            "candidateInputPreservation": preserved, "referenceDeterminism": rd, "candidateDeterminism": cd}


def _execute_object(out, request_path, request_sha, context, repetition, env, timeout, scope):
    validate_environment(context, env)
    key = execution_key(request_sha, context, repetition, scope)
    directory = out / "objects" / key
    directory.mkdir(parents=True)
    target = directory / "request.json"
    shutil.copyfile(request_path, target)
    observation_path = directory / "observation.json"
    argv = [*context["argvTemplate"][:-2], str(target), str(observation_path)]
    record = run(argv, directory, timeout, env=env)
    require(type(record["exitCode"]) is int and record["exitCode"] == 0 and record["timedOut"] is False, "Request process failed: " + key)
    observation = load(observation_path)
    validate_engine(observation, context, request_sha)
    return {"executionKey": key, "requestSha256": request_sha, "contextSha256": canonical_sha(context),
            "role": context["role"], "repetition": repetition,
            "scope": scope,
            "request": target.relative_to(out).as_posix(), "observation": observation_path.relative_to(out).as_posix(),
            "observationSha256": sha256(observation_path),
            "command": record, "commandReceiptSha256": sha256(directory / "command.json")}


def _identity_command(out, name, fingerprint, argv):
    directory = out / name
    require(sha256(directory / "command.json") == fingerprint, "Engine identity command bytes differ")
    record = load(directory / "command.json")
    require(record["argv"] == argv and record["cwd"] == str(ROOT) and type(record["exitCode"]) is int and record["exitCode"] == 0 and
            record["timedOut"] is False, "Engine identity command/isolation differs")
    for stream in ("stdout", "stderr"):
        require(sha256(directory / (stream + ".log")) == record[stream + "Sha256"], "Engine identity command log differs")


def _wheel_identity(out, identity):
    installed = load(out / "installed-wheel.json")
    require(sha256(out / "installed-wheel.json") == identity["installedReceiptSha256"], "Installed receipt bytes differ")
    require(installed["status"] == "INSTALLED_WHEEL_BYTES_MATCH" and installed["isolatedInterpreter"] is True and
            installed["modulePath"] == identity["modulePath"] and installed["wheelSha256"] == identity["wheelSha256"] and
            installed["version"] == identity["version"] and installed["python"] == identity["pythonIdentity"]["version"] and
            installed["packageFilesSha256"] == identity["packageFilesSha256"], "Installed receipt identity differs")
    require(not Path(identity["modulePath"]).resolve().is_relative_to(ROOT / "src"), "Source-tree candidate is not allowed")
    with zipfile.ZipFile(identity["wheel"]) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate wheel member")
        expected = {}
        for name in names:
            if name.startswith("pyelk/") and not name.endswith("/"):
                relative = name[len("pyelk/"):]
                require(relative and "\\" not in relative and not any(p in ("", ".", "..") for p in relative.split("/")), "Unsafe wheel member")
                expected[relative] = hashlib.sha256(archive.read(name)).hexdigest()
        receipt = installed["distributionMetadata"]
        raw_metadata = archive.read(receipt["archivePath"])
        require(hashlib.sha256(raw_metadata).hexdigest() == receipt["sha256"] and
                base64.b64encode(raw_metadata).decode("ascii") == receipt["bytesBase64"], "Actual wheel METADATA differs")
    require(expected == identity["packageFilesSha256"], "Wheel/current installed file denominator differs")
    current_metadata(installed)
    current = {name: fingerprint for name, fingerprint in _tree_files(ROOT / "src/pyelk").items()
               if name.endswith(".py") or name.startswith("_licenses/") or name == "py.typed"}
    require(current == expected, "Old wheel cannot certify changed current sources")


def _current_context_files(out, context):
    validate_environment(context)
    require(context["sourceSha256"] == source_hashes(), "Execution adapter/dependency bytes changed")
    require(context["projectFilesSha256"] == project_identity(), "Current project/README identity changed")
    require(context["upstreamLockSha256"] == sha256(ROOT / "UPSTREAM.json") and
            context["seedPolicySha256"] == sha256(ROOT / "references/e04-determinism-policy.json"), "Baseline/configuration changed")
    identity = context["identity"]
    origin = Path(context["actualExecutionRoot"])
    require(origin.is_absolute() and context["workingDirectory"] == str(ROOT), "Unknown execution root/context")
    if context["role"] == "reference":
        require(identity["name"] == "elkjs" and context["environmentPolicy"] == "NO_NODE_PYTHON_OVERRIDES" and
                context["argvTemplate"] == [identity["node"], str(ROOT / "tools/reference/capture_layout.cjs"), identity["package"], "<REQUEST>", "<OBSERVATION>"],
                "Reference argv/environment policy differs")
        _identity_command(out, "node-identity-command", identity["queryCommandSha256"], [identity["node"], "--version"])
        require((out / "node-identity-command/stdout.log").read_text(encoding="utf-8").strip() == identity["version"], "Actual Node version differs")
        lock = load(ROOT / "UPSTREAM.json")
        require(identity["baseline"] == lock["javascript"]["version"] and
                identity["entrypointSha256"] == lock["distribution"]["sha256Files"]["lib/elk.bundled.js"] and
                all(identity["packageFilesSha256"].get(name) == value for name, value in lock["distribution"]["sha256Files"].items()), "Reference baseline differs")
        require(sha256(Path(identity["node"])) == identity["nodeSha256"] and
                _tree_files(Path(identity["package"])) == identity["packageFilesSha256"], "Reference engine bytes changed")
    else:
        require(context["role"] == "candidate" and identity["name"] == "pyelk" and
                context["environmentPolicy"] == "EMPTY_PATH_NO_PYTHON_OVERRIDES" and
                context["argvTemplate"] == [identity["python"], "-I", str(ROOT / "scripts/run_pyelk_candidate.py"), "<REQUEST>", "<OBSERVATION>"],
                "Candidate argv/isolation/environment policy differs")
        _identity_command(out, "candidate-identity-command", identity["queryCommandSha256"], [identity["python"], "-I", "-c", VERSION_QUERY])
        require(load(out / "candidate-identity-command/stdout.log") == identity["pythonIdentity"] and
                identity["pythonIdentity"]["isolated"] is True, "Actual Python identity differs")
        _identity_command(out, "installed-wheel-command", identity["installedCommandSha256"],
                          [identity["python"], "-I", str(ROOT / "scripts/verify_installed_wheel.py"), identity["wheel"], "--out", str(origin / "installed-wheel.json")])
        _wheel_identity(out, identity)
        require(all(sha256(Path(path)) == fingerprint for path, fingerprint in identity["binariesSha256"].items()) and
                sha256(Path(identity["wheel"])) == identity["wheelSha256"], "Candidate interpreter/wheel bytes changed")
        actual = _tree_files(Path(identity["modulePath"]))
        require(actual == identity["packageFilesSha256"], "Installed candidate changed")


def _jobs(plan, contexts, repeat, reuse):
    if reuse:
        requests = [(fingerprint, request["request"], {"kind": "request"}) for fingerprint, request in plan["requests"].items()]
    else:
        requests = [(case["requestSha256"], case["request"], {"kind": "case", "suite": name, "caseId": case["caseId"]})
                    for name, suite in plan["suites"].items() for case in suite["cases"]]
    return [(fingerprint, request, scope, role, i) for fingerprint, request, scope in requests for role in contexts for i in range(repeat)]


def verify_objects(out, plan, contexts, objects, repeat, *, reuse=True):
    """Check actual objects and argv; a shared object is never another execution."""
    require(set(contexts) == {"reference", "candidate"}, "Engine context denominator differs")
    require(contexts["reference"]["nonce"] == contexts["candidate"]["nonce"] and
            contexts["reference"]["actualExecutionRoot"] == contexts["candidate"]["actualExecutionRoot"],
            "Objects cannot be combined across actual runs")
    expected = {execution_key(h, contexts[role], i, scope) for h, _, scope, role, i in _jobs(plan, contexts, repeat, reuse)}
    require(set(objects) == expected and len(objects) == (len(plan["requests"]) if reuse else plan["caseCount"]) * 2 * repeat, "Execution/repetition denominator differs")
    for key, row in objects.items():
        role, repetition, fingerprint = row["role"], row["repetition"], row["requestSha256"]
        require(role in contexts and key == row["executionKey"] == execution_key(fingerprint, contexts[role], repetition, row["scope"]), "Execution key/role differs")
        require(row["contextSha256"] == canonical_sha(contexts[role]), "Object context differs")
        request, observed_path = contained(out, row["request"]), contained(out, row["observation"])
        directory = out / "objects" / key
        require(request == directory / "request.json" and observed_path == directory / "observation.json", "Object paths/slot differ")
        require(sha256(request) == fingerprint and sha256(observed_path) == row["observationSha256"], "Object raw bytes differ")
        require(request.read_bytes() == contained(ROOT, plan["requests"][fingerprint]["request"]).read_bytes(), "Object request is not original")
        record = load(directory / "command.json")
        require(sha256(directory / "command.json") == row["commandReceiptSha256"] and record == row["command"], "Actual command receipt differs")
        origin = Path(contexts[role]["actualExecutionRoot"]) / "objects" / key
        require(record["argv"] == [*contexts[role]["argvTemplate"][:-2], str(origin / "request.json"), str(origin / "observation.json")] and
                record["cwd"] == str(ROOT) and type(record["exitCode"]) is int and record["exitCode"] == 0 and record["timedOut"] is False,
                "Actual command role/isolation/slot differs")
        for stream in ("stdout", "stderr"):
            require(sha256(directory / (stream + ".log")) == record[stream + "Sha256"], "Actual process log differs")
        validate_engine(load(observed_path), contexts[role], fingerprint)


def evaluate_plan(out, plan, contexts, objects, repeat, *, reuse=True):
    verify_objects(out, plan, contexts, objects, repeat, reuse=reuse)
    reports = {}
    for name, suite in plan["suites"].items():
        rows = []
        for case in suite["cases"]:
            fingerprint = case["requestSha256"]
            scope = {"kind": "request"} if reuse else {"kind": "case", "suite": name, "caseId": case["caseId"]}
            keys = {role: [execution_key(fingerprint, contexts[role], i, scope) for i in range(repeat)] for role in contexts}
            observations = {role: [load(contained(out, objects[key]["observation"])) for key in keys[role]] for role in contexts}
            row = evaluate_case(case["definition"], contained(ROOT, case["request"]), observations["reference"], observations["candidate"], repeat)
            row["executionReferences"] = keys
            rows.append(row)
        reports[name] = {"caseCount": len(rows), "passed": all(row["passed"] for row in rows), "cases": rows}
    return reports


def validate_timing(report, objects, identity_commands):
    """Necessary clock/concurrency consistency, not historical authentication."""
    def duration(value):
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0, "Invalid measured duration")
        return value
    jobs = report["jobs"]
    require(type(jobs) is int and 1 <= jobs <= 16, "Unknown measured concurrency")
    capture, elapsed = (duration(report[key]) for key in ("captureSeconds", "elapsedSeconds"))
    layout = [duration(row["command"]["elapsedSeconds"]) for row in objects.values()]
    identity = [duration(row["elapsedSeconds"]) for row in identity_commands]
    require(bool(layout) and len(identity) == 3, "Missing measured process durations")
    # Each subprocess timer is rounded to6 decimals. Bound the aggregate
    # rounding error explicitly rather than widening layout tolerances.
    rounding = (len(layout) + len(identity) + 2) * 1e-6
    require(capture + rounding >= max(layout) and capture + rounding >= sum(layout) / jobs,
            "Capture duration contradicts actual process/concurrency receipts")
    require(elapsed + rounding >= capture + sum(identity), "Total duration contradicts capture/identity receipts")


def identity_commands(out):
    return [load(out / name / "command.json") for name in
            ("candidate-identity-command", "node-identity-command", "installed-wheel-command")]


def execute(args):
    out = args.out.resolve()
    require(out.is_relative_to(ROOT / "test-runs") and not out.is_relative_to(args.package.resolve()),
            "Use a new test-runs directory outside the reference package")
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    plan = build_plan()
    write(out / "plan.json", plan)
    envs = environments()
    contexts = create_contexts(out, args.candidate_python, args.wheel, args.package, args.node, envs)
    for context in contexts.values():
        context["concurrency"] = args.jobs
    write(out / "contexts.json", contexts)
    objects = {}
    mode = "independent-case" if args.no_reuse else "shared-request"
    manifest = {"schema": "py-elk-request-execution-objects/v1", "repeat": args.repeat, "executionMode": mode, "objects": objects}
    capture_started = time.monotonic()
    try:
        jobs = _jobs(plan, contexts, args.repeat, not args.no_reuse)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(_execute_object, out, contained(ROOT, request), fingerprint, contexts[role], repetition,
                                   envs[role], args.timeout, scope) for fingerprint, request, scope, role, repetition in jobs]
            try:
                for ordinal, future in enumerate(as_completed(futures), 1):
                    row = future.result()
                    objects[row["executionKey"]] = row
                    if ordinal % 150 == 0:
                        print(f"Executed {ordinal}/{len(jobs)} actual layout processes", flush=True)
            except Exception:
                for future in futures:
                    future.cancel()
                raise
        capture_seconds = time.monotonic() - capture_started
        write(out / "objects.json", manifest)
        suites = evaluate_plan(out, plan, contexts, objects, args.repeat, reuse=not args.no_reuse)
        write(out / "suite-results.json", suites)
        require(plan == build_plan(), "Original suite/request bytes changed during run")
        for role in contexts:
            _current_context_files(out, contexts[role])
            validate_environment(contexts[role], envs[role])
        passed = all(row["passed"] for row in suites.values())
        report = {"schema": "py-elk-suite-execution-run/v1", "status": "SUITE_EXECUTION_REUSE_PASS" if passed else "FAIL",
                  "passed": passed, "caseCount": plan["caseCount"], "uniqueRequests": plan["uniqueRequests"],
                  "repeat": args.repeat, "actualLayoutProcesses": len(objects),
                  "executionMode": mode, "jobs": args.jobs,
                  "unsharedLayoutProcesses": plan["caseCount"] * 2 * args.repeat,
                  "savedLayoutProcesses": plan["caseCount"] * 2 * args.repeat - len(objects),
                  "captureSeconds": round(capture_seconds, 6), "elapsedSeconds": round(time.monotonic() - started, 6),
                  "suiteCounts": {name: row["caseCount"] for name, row in suites.items()},
                  "filesSha256": {name: sha256(out / name) for name in ("plan.json", "contexts.json", "objects.json", "suite-results.json", "installed-wheel.json")},
                  "sourceSha256": source_hashes(), "pythonAlgorithmsVerified": 0, "packagePublished": False,
                  "limitation": "Explicit actual fresh-process execution; shared-request mode only reuses within this run. Original cases/policies are all evaluated. No old capture index/export receipt is synthesized; no cross-run/candidate reuse. Duration and recorded environment consistency do not authenticate historical clocks, environment values or execution; read-only verification does not compare its caller environment to the original execution environment."}
        validate_timing(report, objects, identity_commands(out))
        write(out / "report.json", report)
        return report
    except Exception as error:
        if not (out / "objects.json").exists():
            write(out / "objects.json", manifest)
        write(out / "failure.json", {"status": "FAIL", "objectsCompleted": len(objects), "error": str(error)})
        raise


def verify_run(out):
    out = Path(out).resolve()
    report = load(out / "report.json")
    require(report["schema"] == "py-elk-suite-execution-run/v1" and report["status"] == "SUITE_EXECUTION_REUSE_PASS" and report["passed"] is True,
            "A successful actual reuse run is required")
    require(type(report["repeat"]) is int and report["repeat"] >= 3, "Independent repetition count differs")
    require(report["executionMode"] in ("shared-request", "independent-case") and type(report["jobs"]) is int and 1 <= report["jobs"] <= 16,
            "Unknown execution mode/concurrency")
    reuse = report["executionMode"] == "shared-request"
    expected_names = {"plan.json", "contexts.json", "objects.json", "suite-results.json", "installed-wheel.json"}
    require(set(report["filesSha256"]) == expected_names, "Reuse receipt file denominator differs")
    for name, fingerprint in report["filesSha256"].items():
        require(sha256(out / name) == fingerprint, "Reuse receipt bytes differ: " + name)
    plan, contexts, manifest = (load(out / name) for name in ("plan.json", "contexts.json", "objects.json"))
    require(plan == build_plan() and report["sourceSha256"] == source_hashes(), "Current requests/dependencies differ")
    require(manifest["schema"] == "py-elk-request-execution-objects/v1" and manifest["repeat"] == report["repeat"] and
            manifest["executionMode"] == report["executionMode"], "Execution manifest differs")
    require(report["caseCount"] == plan["caseCount"] and report["uniqueRequests"] == plan["uniqueRequests"] and
            report["actualLayoutProcesses"] == len(manifest["objects"]) == (plan["uniqueRequests"] if reuse else plan["caseCount"]) * 2 * report["repeat"] and
            report["unsharedLayoutProcesses"] == plan["caseCount"] * 2 * report["repeat"] and
            report["savedLayoutProcesses"] == report["unsharedLayoutProcesses"] - report["actualLayoutProcesses"], "Case/process denominator differs")
    for role in contexts:
        _current_context_files(out, contexts[role])
        require(contexts[role]["concurrency"] == report["jobs"], "Concurrency context differs")
    suites = evaluate_plan(out, plan, contexts, manifest["objects"], report["repeat"], reuse=reuse)
    require(suites == load(out / "suite-results.json") and all(s["passed"] for s in suites.values()), "Per-case policy/repetition results differ")
    require(report["suiteCounts"] == {name: row["caseCount"] for name, row in suites.items()}, "Original suite denominators differ")
    validate_timing(report, manifest["objects"], identity_commands(out))
    return {"status": "SUITE_EXECUTION_REUSE_RECEIPT_VALIDATED", "passed": True,
            "caseCount": plan["caseCount"], "uniqueRequests": plan["uniqueRequests"], "actualLayoutProcesses": len(manifest["objects"]),
            "runtimeReexecuted": False, "historicalExecutionAuthenticated": False,
            "environmentVerification": "RECORDED_POLICY_AND_CONTEXT_BINDING_ONLY",
            "currentCallerEnvironmentCompared": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("plan");p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--candidate-python", type=Path, required=True)
    p.add_argument("--wheel", type=Path, required=True)
    p.add_argument("--package", type=Path, default=ROOT / ".local/npm-elkjs/package")
    p.add_argument("--node", default="node");p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--jobs", type=int, default=2);p.add_argument("--no-reuse", action="store_true")
    p.add_argument("--timeout", type=float, default=30);p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("verify");p.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "plan":
            result = build_plan();write(args.out, result)
            print(json.dumps({key: result[key] for key in ("caseCount", "uniqueRequests", "duplicateRequestsPerEngineRepeat")}, indent=2));return 0
        if args.action == "run":
            require(args.repeat >= 3 and 0 < args.timeout <= 300 and 1 <= args.jobs <= 16,
                    "Use >=3 repetitions, timeout in(0,300] and jobs in[1,16]")
            result = execute(args)
        else:
            result = verify_run(args.directory)
        print(json.dumps({key: result[key] for key in ("status", "passed", "caseCount", "uniqueRequests", "actualLayoutProcesses")}, indent=2))
        return 0 if result["passed"] else 1
    except (ValueError, OSError, KeyError, TypeError, IndexError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
