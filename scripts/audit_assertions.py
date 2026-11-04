"""Index locked upstream Mocha source without executing or counting runtime assertions.

Static lexical call-sites are research evidence, not assertion/pass denominators.
Canonical bodies come from git-show at UPSTREAM's exact commit, never worktree text.
Offline check validates the saved index and current project request fingerprints;
--with-upstream additionally regenerates it from canonical Git blobs.
"""
from __future__ import annotations

import argparse
import bisect
from dataclasses import dataclass
import hashlib
import json
import keyword
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "py-elk-assertion-inventory/v1"
PROJECT_RELATIONSHIP = "topic_only; not copied input, assertion coverage, or an upstream test result"
CASE_CALLS = {"it", "xit", "specify", "xspecify"}
SUITE_CALLS = {"describe", "xdescribe", "context", "xcontext"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(checkout: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(checkout), *args], stderr=subprocess.PIPE)


def location(text: str, start: int, end: int) -> dict:
    offsets = [0, *[m.end() for m in re.finditer("\n", text)]]
    line = bisect.bisect_right(offsets, start)
    end_line = bisect.bisect_right(offsets, max(start, end - 1))
    return {"line": line, "column": start - offsets[line - 1] + 1, "endLine": end_line,
            "startByte": len(text[:start].encode("utf-8")), "endByte": len(text[:end].encode("utf-8"))}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


def lex(text: str):
    """Small conservative lexical scanner; not a JavaScript parser or evaluator."""
    tokens, comments, opaque = [], [], []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        start = i
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            comments.append(Token("comment", text[start:i], start, i))
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated JavaScript comment")
            i = end + 2
            comments.append(Token("comment", text[start:i], start, i))
            continue
        if ch in "\"'`":
            quote = ch
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError("Unterminated JavaScript string/template")
            kind = "template" if quote == "`" else "string"
            token = Token(kind, text[start:i], start, i)
            tokens.append(token)
            if kind == "template":
                opaque.append({"kind": "template_literal_not_expanded", **location(text, start, i)})
            continue
        # Treat likely regex literals as opaque so their punctuation cannot form tests.
        previous = tokens[-1].value if tokens else ""
        if ch == "/" and previous in ("", "=", "(", "[", ",", ":", "return", "=>", "!"):
            i += 1
            in_class = False
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "[":
                    in_class = True
                elif text[i] == "]":
                    in_class = False
                elif text[i] == "/" and not in_class:
                    i += 1
                    while i < len(text) and text[i].isalpha():
                        i += 1
                    break
                elif text[i] in "\r\n":
                    raise ValueError("Unterminated likely JavaScript regex")
                i += 1
            else:
                raise ValueError("Unterminated likely JavaScript regex")
            tokens.append(Token("regex", text[start:i], start, i))
            continue
        match = re.match(r"[A-Za-z_$][\w$]*|(?:\d+(?:\.\d*)?)|=>|===|!==|==|!=|&&|\|\||\?\.", text[i:])
        if match:
            value = match[0]
            i += len(value)
            tokens.append(Token("word" if re.match(r"[A-Za-z_$]", value) else "other", value, start, i))
        else:
            i += 1
            tokens.append(Token("punctuation", ch, start, i))
    return tokens, comments, opaque


def paired(tokens):
    stack, result = [], {}
    closes = {")": "(", "]": "[", "}": "{"}
    for i, token in enumerate(tokens):
        if token.kind in ("string", "template", "regex"):
            continue
        if token.value in ("(", "[", "{"):
            stack.append((token.value, i))
        elif token.value in closes:
            if not stack or stack[-1][0] != closes[token.value]:
                raise ValueError("Unbalanced JavaScript delimiters")
            _, start = stack.pop()
            result[start], result[i] = i, start
    if stack:
        raise ValueError("Unbalanced JavaScript delimiters")
    return result


def literal_title(token):
    if token.kind != "string":
        return None
    # Preserve the original title spelling; no JavaScript string evaluation.
    return token.value[1:-1]


def registration(tokens, pairs, i):
    token = tokens[i]
    if token.kind != "word" or token.value not in CASE_CALLS | SUITE_CALLS or (i and tokens[i - 1].value in (".", "?.", "function")):
        return None
    j, mode = i + 1, "normal"
    if j + 1 < len(tokens) and tokens[j].value == "." and tokens[j + 1].value in ("skip", "only"):
        mode, j = tokens[j + 1].value, j + 2
    if j >= len(tokens) or tokens[j].value != "(":
        return None
    end = pairs[j]
    if j + 1 >= end:
        return None
    comma = j + 1
    while comma < end and tokens[comma].value != ",":
        comma = pairs[comma] + 1 if tokens[comma].value in ("(", "[", "{") else comma + 1
    body = next((k for k in range(comma + 1, end) if tokens[k].value == "{"), None)
    body_end = pairs[body] if body is not None else end
    return {"callIndex": i, "start": token.start, "end": tokens[end].end,
            "bodyStart": tokens[body].start if body is not None else tokens[comma].end,
            "bodyEnd": tokens[body_end].end, "title": literal_title(tokens[j + 1]),
            "mode": "skip" if token.value.startswith("x") else mode,
            "kind": "case" if token.value in CASE_CALLS else "suite"}


def chain_end(tokens, pairs, i):
    """Return a lexical root/chain span and its top-level property names."""
    end, properties = i, []
    if i + 1 < len(tokens) and tokens[i + 1].value == "(":
        end = pairs[i + 1]
    while end + 2 < len(tokens) and tokens[end + 1].value in (".", "?.") and tokens[end + 2].kind == "word":
        end += 2
        properties.append(tokens[end].value)
        if end + 1 < len(tokens) and tokens[end + 1].value == "(":
            end = pairs[end + 1]
    return tokens[end].end, properties


def topic(path, title):
    name = Path(path).name
    groups = {
        "testParameters.js": ["api-parameters", "errors"],
        "testIds.js": ["json-id-validation", "errors"],
        "testOptions.js": ["options", "defaults-and-precedence"],
        "testLogging.js": ["logging-and-timing", "input-side-effects"],
        "testEntryPoints.js": ["host-entrypoints", "lifecycle"],
        "test-node.js": ["host-entrypoints"],
        "testRaiseException.js": ["algorithm-selection", "errors"],
        "testLayouters.js": ["other-algorithms", "given-geometry"],
        "test-bug-8.js": ["hierarchy", "edge-format", "errors"],
        "test-bug-7.js": ["ports", "regression"],
        "test-bug-63.js": ["self-loop", "layered-strategy", "regression"],
        "test-bug-klay-22.js": ["labels", "regression"],
        "test-bug-klay-23.js": ["given-geometry", "layered-strategy", "regression"],
        "testChangeAwareArrayList.js": ["large-graph", "regression"]
    }.get(name, ["unclassified"])
    lower = (title or "").lower()
    if "padding" in lower:
        groups += ["padding"]
    if "invalid layouter" in lower or "no layouter" in lower:
        groups += ["algorithm-selection"]
    return sorted(set(groups))


def targets(groups):
    symbols = set()
    mapping = {"project-basic-layered": "pyelk.algorithms.layered.pipeline", "api-parameters": "pyelk.elk.ELK.layout", "json-id-validation": "pyelk.model.validation.validate_id",
               "errors": "pyelk.errors.ELKError", "options": "pyelk.options.resolve.resolve_options",
               "defaults-and-precedence": "pyelk.options.resolve.resolve_options", "padding": "pyelk.geometry.padding.parse_padding",
               "algorithm-selection": "pyelk.metadata.registry.resolve_algorithm", "logging-and-timing": "pyelk.execution.context.ExecutionContext",
               "input-side-effects": "pyelk.model.adapter.export_graph", "host-entrypoints": "pyelk.elk.ELK",
               "lifecycle": "pyelk.execution.context.ExecutionContext", "other-algorithms": "pyelk.algorithms.registry",
               "given-geometry": "pyelk.model.adapter.import_graph", "hierarchy": "pyelk.execution.hierarchy.layout_hierarchy",
               "edge-format": "pyelk.model.adapter.import_graph", "ports": "pyelk.model.ports",
               "self-loop": "pyelk.algorithms.layered.routing", "layered-strategy": "pyelk.algorithms.layered.pipeline",
               "labels": "pyelk.geometry.labels", "large-graph": "pyelk.algorithms.layered.pipeline",
               "regression": "pyelk.algorithms.layered.pipeline"}
    for group in groups:
        if group in mapping:
            symbols.add(mapping[group])
    return [{"symbol": symbol, "status": "planned", "existsClaimed": False} for symbol in sorted(symbols)]


def valid_planned_targets(items):
    """A mapping requires named Python symbols, not empty or fabricated targets."""
    return isinstance(items, list) and bool(items) and all(
        isinstance(item, dict) and item.get("status") == "planned" and item.get("existsClaimed") is False
        and isinstance(item.get("symbol"), str) and bool(item["symbol"])
        and all(part.isidentifier() and not keyword.iskeyword(part) for part in item["symbol"].split("."))
        for item in items)


def scan_source(path: str, data: bytes):
    text = data.decode("utf-8")
    tokens, comments, opaque = lex(text)
    pairs = paired(tokens)
    registrations = [r for i in range(len(tokens)) if (r := registration(tokens, pairs, i))]
    suites = [r for r in registrations if r["kind"] == "suite"]
    cases = []
    declared_cases = [r for r in registrations if r["kind"] == "case"]
    for ordinal, case in enumerate(declared_cases, 1):
        identity = f"elkjs:{Path(path).stem}:it:{ordinal:03d}"
        groups = topic(path, case["title"])
        sites, calls, controls = [], [], []
        for i, token in enumerate(tokens):
            if not case["bodyStart"] < token.start < case["bodyEnd"]:
                continue
            if any(other is not case and case["bodyStart"] < other["bodyStart"] < token.start < other["bodyEnd"] < case["bodyEnd"] for other in declared_cases):
                continue
            previous = tokens[i - 1].value if i else ""
            following = tokens[i + 1].value if i + 1 < len(tokens) else ""
            kind = None
            if token.value in ("expect", "assert") and token.kind == "word" and following == "(" and previous not in (".", "?.", "function"):
                kind = token.value
            elif token.value == "should" and previous == "." and following != "(":
                kind = "should-chain"
            if kind:
                end, chain = chain_end(tokens, pairs, i)
                sites.append({"id": identity + f":site:{len(sites) + 1:03d}", "kind": kind,
                              "location": location(text, token.start, end), "chainProperties": chain,
                              "expressionSha256": digest(text[token.start:end].encode("utf-8")),
                              "pythonTargets": targets(groups), "executionStatus": "not_executed"})
            if previous == "." and following == "(" and token.value in ("layout", "terminateWorker", "knownLayoutAlgorithms", "knownLayoutOptions", "knownLayoutCategories"):
                calls.append({"method": token.value, **location(text, token.start, token.end)})
            if token.kind == "word" and token.value in ("for", "while", "if", "switch", "catch"):
                controls.append({"kind": token.value, **location(text, token.start, token.end)})
        cases.append({"id": identity, "title": case["title"], "mode": case["mode"],
                      "suites": [s["title"] for s in suites if s["bodyStart"] < case["start"] < s["bodyEnd"]],
                      "location": location(text, case["start"], case["end"]), "behaviorGroups": groups,
                      "assertionSites": sites, "apiCallSites": calls, "controlFlowSites": controls,
                      "dynamicTitle": case["title"] is None, "pythonTargets": targets(groups),
                      "executionStatus": "not_executed"})
    todo = [{"location": location(text, c.start, c.end), "commentSha256": digest(c.value.encode())}
            for c in comments if re.search(r"\b(?:TODO|FIXME)\b", c.value)]
    registration_controls = [{"kind": t.value, **location(text, t.start, t.end)} for t in tokens
                             if t.kind == "word" and t.value in ("for", "while", "forEach", "eval")]
    return {"testCases": cases, "staticTestCaseSites": len(cases),
            "staticAssertionRootSites": sum(len(c["assertionSites"]) for c in cases),
            "todoCommentSites": todo, "opaqueSyntaxSites": opaque, "possibleDynamicRegistrationSites": registration_controls}


def project_groups(case):
    identity = case["id"]
    groups = {"project-basic-layered"}
    if identity.startswith("options-"):
        groups |= {"options", "defaults-and-precedence"}
    if "spacing" in identity:
        groups |= {"options", "padding"}
    if "self-loop" in identity:
        groups.add("self-loop")
    if identity.startswith("error-"):
        groups.add("errors")
    if identity == "error-missing-graph":
        groups.add("api-parameters")
    if identity == "error-unknown-algorithm":
        groups.add("algorithm-selection")
    return sorted(groups)


def build(root: Path = ROOT, checkout: Path | None = None):
    lock = load(root / "UPSTREAM.json")
    commit = lock["javascript"]["commit"]
    checkout = checkout or root / ".local/upstream-elkjs"
    expected = {s["path"]: s["gitBlob"] for s in load(root / "references/source-inventory.json")["files"]
                if s["category"] == "test_source"}
    tree = git(checkout, "ls-tree", "-r", "-z", commit, "--", "test/mocha/")
    found = {}
    for record in tree.rstrip(b"\0").split(b"\0"):
        info, name = record.decode("utf-8").split("\t", 1)
        _, kind, blob = info.split()
        if kind == "blob":
            found[name] = blob
    if found != expected:
        raise ValueError("Canonical Mocha file denominator/blob identity differs from source inventory")
    sources = []
    for path, blob in sorted(found.items()):
        data = git(checkout, "show", commit + ":" + path)
        actual_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual_blob != blob:
            raise ValueError("Canonical Git blob content identity differs")
        spdx = re.search(rb"SPDX-License-Identifier:\s*([^\r\n]+)", data)
        sources.append({"path": path, "commit": commit, "gitBlob": blob, "sha256": digest(data),
                        "byteCount": len(data), "lineCount": len(data.decode().splitlines()),
                        "spdx": spdx[1].decode().strip() if spdx else None,
                        "sourceMode": "canonical-git-blob", **scan_source(path, data)})
    all_cases = [case for source in sources for case in source["testCases"]]
    fixture_path = root / "tests/fixtures/validation/cases.json"
    fixtures = load(fixture_path)
    project_cases = []
    for case in fixtures["cases"]:
        request = (fixture_path.parent / case["request"]).resolve()
        if not request.is_relative_to(fixture_path.parent.resolve()) or not request.is_file():
            raise ValueError("Project request path is missing or escaping")
        groups = project_groups(case)
        related = [u["id"] for u in all_cases if set(groups) & set(u["behaviorGroups"])]
        project_cases.append({"id": "project:" + case["id"], "caseId": case["id"], "origin": "project-authored",
                              "request": request.relative_to(root).as_posix(), "requestSha256": digest(request.read_bytes()),
                              "behaviorGroups": groups, "relatedUpstreamCaseIds": related,
                              "relationship": PROJECT_RELATIONSHIP,
                              "expectedOutcome": case["expectedOutcome"], "pythonTargets": targets(groups),
                              "pythonExecutionStatus": "not_implemented"})
    return {"schema": SCHEMA, "baseline": {"version": lock["javascript"]["version"], "commit": commit,
                                           "repository": lock["javascript"]["repository"]},
            "scanner": {"kind": "conservative-lexical-static-index", "input": "git show <locked commit>:<path>",
                        "assertionRootKinds": ["assert", "expect", "should-chain"],
                        "doesNotExpand": ["runtime loops/conditions", "parameterization", "templates/eval", "Chai chained assertion semantics", "Java algorithm test suites"],
                        "doesNotResolve": ["identifier aliasing/shadowing", "arbitrary computed member calls", "full JavaScript grammar"],
                        "worktreeTextUsed": False},
            "sources": sources, "projectFixtureManifestSha256": digest(fixture_path.read_bytes()), "projectCases": project_cases,
            "totals": {"upstreamSourceFiles": len(sources), "staticTestCaseSites": len(all_cases),
                       "staticAssertionRootSites": sum(s["staticAssertionRootSites"] for s in sources),
                       "projectCases": len(project_cases), "upstreamTestsExecuted": 0, "pythonAlgorithmsVerified": 0,
                       "expandedIndependentAssertionDenominator": None},
            "openItems": [
                {"id": "ASSERT-001", "state": "open", "nextAction": "Expand each Chai chain and dynamic registration into separately identified assertions; lexical roots are not assertion totals."},
                {"id": "ASSERT-002", "state": "open", "nextAction": "Reproduce upstream tests with the exact entrypoint/worker and dependency versions in an isolated development run; no upstream Mocha execution is claimed here."},
                {"id": "ASSERT-003", "state": "open", "nextAction": "Build explicit first-release assertion-to-candidate mappings; project topic links do not establish coverage, including default/empty replacement, ID edge cases and logging reuse."},
                {"id": "ASSERT-004", "state": "open", "nextAction": "Add Java algorithm source assertions after exact component lineage is established; the fourteen JS files are not the full ELK test denominator."}
            ], "limitation": "Static locations and topic links only. No upstream test pass count, complete assertion coverage, Python implementation or coordinate acceptance."}


def validate_snapshot(index, root: Path = ROOT):
    if index.get("schema") != SCHEMA:
        raise ValueError("Invalid assertion index schema")
    lock = load(root / "UPSTREAM.json")
    if index["baseline"]["commit"] != lock["javascript"]["commit"] or index["baseline"]["version"] != lock["javascript"]["version"]:
        raise ValueError("Assertion index baseline differs")
    expected = {s["path"]: s["gitBlob"] for s in load(root / "references/source-inventory.json")["files"] if s["category"] == "test_source"}
    if {s["path"]: s["gitBlob"] for s in index["sources"]} != expected or len(index["sources"]) != len(expected):
        raise ValueError("Assertion source file denominator/blob identity differs")
    identities, site_count, case_count = set(), 0, 0
    for source in index["sources"]:
        if source["commit"] != index["baseline"]["commit"] or source["sourceMode"] != "canonical-git-blob" or not re.fullmatch("[0-9a-f]{64}", source["sha256"]):
            raise ValueError("Invalid canonical source identity")
        for case in source["testCases"]:
            case_count += 1
            items = [case, *case["assertionSites"]]
            site_count += len(case["assertionSites"])
            for item in items:
                if item["id"] in identities:
                    raise ValueError("Duplicate case/assertion ID")
                identities.add(item["id"])
                loc = item["location"]
                if not 1 <= loc["line"] <= loc["endLine"] <= source["lineCount"] or not 0 <= loc["startByte"] < loc["endByte"] <= source["byteCount"]:
                    raise ValueError("Case/assertion location outside canonical source")
                if item["executionStatus"] != "not_executed" or not valid_planned_targets(item.get("pythonTargets")):
                    raise ValueError("Static source index cannot claim execution or implementation and requires valid planned Python symbols")
        if source["staticTestCaseSites"] != len(source["testCases"]) or source["staticAssertionRootSites"] != sum(len(c["assertionSites"]) for c in source["testCases"]):
            raise ValueError("Per-source static counts differ")
    manifest_path = root / "tests/fixtures/validation/cases.json"
    manifest = load(manifest_path)
    if digest(manifest_path.read_bytes()) != index["projectFixtureManifestSha256"] or [c["id"] for c in manifest["cases"]] != [c["caseId"] for c in index["projectCases"]]:
        raise ValueError("Project case denominator/fingerprint differs")
    upstream_ids = {c["id"] for source in index["sources"] for c in source["testCases"]}
    for project, master in zip(index["projectCases"], manifest["cases"]):
        path = (root / project["request"]).resolve()
        master_request = (manifest_path.parent / master["request"]).resolve()
        if (path != master_request or not path.is_relative_to(manifest_path.parent.resolve())
                or digest(path.read_bytes()) != project["requestSha256"]):
            raise ValueError("Project request fingerprint differs")
        if (project["id"] != "project:" + master["id"] or project["expectedOutcome"] != master["expectedOutcome"]
                or project["origin"] != "project-authored" or not set(project["relatedUpstreamCaseIds"]) <= upstream_ids):
            raise ValueError("Project/upstream provenance differs")
        if (project["pythonExecutionStatus"] != "not_implemented" or project["relationship"] != PROJECT_RELATIONSHIP
                or not valid_planned_targets(project.get("pythonTargets"))):
            raise ValueError("Project topic index cannot claim execution, implementation or assertion coverage and requires valid planned Python symbols")
    actual = {"upstreamSourceFiles": len(expected), "staticTestCaseSites": case_count, "staticAssertionRootSites": site_count,
              "projectCases": len(manifest["cases"]), "upstreamTestsExecuted": 0, "pythonAlgorithmsVerified": 0,
              "expandedIndependentAssertionDenominator": None}
    if index["totals"] != actual:
        raise ValueError("Static totals differ or execution/coverage claims were added")
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("generate", "check"))
    parser.add_argument("--checkout", type=Path, default=ROOT / ".local/upstream-elkjs")
    parser.add_argument("--index", type=Path, default=ROOT / "references/assertion-inventory.json")
    parser.add_argument("--out", type=Path, help="New JSON file for generation or check report")
    parser.add_argument("--with-upstream", action="store_true", help="Regenerate from canonical Git objects and compare the entire saved index")
    args = parser.parse_args()
    try:
        if args.action == "generate":
            if args.out is None:
                parser.error("generate requires --out NEW_FILE")
            result = build(checkout=args.checkout)
            validate_snapshot(result)
        else:
            result = load(args.index)
            counts = validate_snapshot(result)
            if args.with_upstream and result != build(checkout=args.checkout):
                raise ValueError("Saved assertion index differs from canonical regeneration")
            result = {"status": "ASSERTION_INDEX_CANONICAL_VERIFIED" if args.with_upstream else "ASSERTION_INDEX_STRUCTURE_VERIFIED", **counts,
                      "limitation": "Static index only; no source execution or Python layout acceptance."}
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        summary = {"status": "ASSERTION_INDEX_GENERATED", "totals": result["totals"]} if args.action == "generate" else result
        print(json.dumps(summary, indent=2))
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "ASSERTION_AUDIT_ERROR", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
