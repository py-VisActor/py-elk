"""Extract actual source phase snapshots from trace_e05_dag.cjs output.

No positions or expected values are recomputed. The archive is development-only
input for private phase tests, never runtime data or public layout acceptance.
"""
import argparse
import base64
from pathlib import Path

from layout_checks import ROOT, load, sha256, write
from validate_e04_runtime import exact

WORKER_SHA = "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86"


def export(capture, request, stage, *, iteration="E05"):
    if iteration not in ("E05", "E06"):
        raise ValueError("Unknown source observation iteration")
    prefix = "py-elk-" + iteration.lower()
    capture, request = Path(capture).resolve(), Path(request).resolve()
    summary = load(capture / "summary.json")
    engines = {kind: load(capture / (kind + ".json")) for kind in ("bundled", "pretty", "instrumented")}
    trace = engines["instrumented"]
    if summary["schema"] != prefix + "-phase-trace/v1" or summary["workerSha256"] != WORKER_SHA:
        raise ValueError("Fixed source trace identity differs")
    for key in ("prettyResultExactToBundled", "instrumentedResultExactToPretty",
                "prettyInputExactToBundled", "instrumentedInputExactToPretty"):
        if summary[key] is not True:
            raise ValueError("Instrumented/original observations differ: " + key)
    if set(summary["outcomes"].values()) != {"returned"}:
        raise ValueError("Actual source execution did not return")
    tool = ROOT / ("tools/reference/trace_e06_graph.cjs" if iteration == "E06" else "tools/reference/trace_e05_dag.cjs")
    if summary["toolSha256"] != sha256(tool):
        raise ValueError("Current observer differs from its producer receipt")
    request_sha = sha256(request)
    if summary["requestSha256"] != request_sha:
        raise ValueError("Original request bytes differ")
    original = load(request)
    for kind, observation in engines.items():
        if (observation["schema"] != prefix + "-phase-observation/v1" or observation["kind"] != kind
                or observation["requestSha256"] != request_sha or observation["workerSha256"] != WORKER_SHA
                or observation["toolSha256"] != summary["toolSha256"] or observation["outcome"] != "returned"):
            raise ValueError("Actual producer identity/outcome differs: " + kind)
        exact(observation["actualLayoutArguments"], original["layoutArguments"], "Producer changed original layout arguments")
    for kind in ("pretty", "instrumented"):
        for key in ("result", "inputAfter"):
            exact(engines[kind][key], engines["bundled"][key], "Actual three-engine " + key + " differs")
    exact([{key: phase[key] for key in ("index", "name", "strategy")} for phase in trace["phases"]],
          [{key: phase[key] for key in ("index", "name", "strategy")} for phase in summary["calls"]],
          "Actual processor call order differs from summary")
    matches = [phase for phase in trace["phases"] if phase["name"].endswith("." + stage)]
    if not matches:
        raise ValueError("No actual matching processor call; empty graphs execute no phases")
    return {"schema": prefix + "-extracted-phases/v1", "stage": stage,
            "requestSha256": request_sha, "requestBytesBase64": base64.b64encode(request.read_bytes()).decode("ascii"),
            "workerSha256": WORKER_SHA, "toolSha256": summary["toolSha256"],
            "producerFilesSha256": {name: sha256(capture / name) for name in
                                    ("summary.json", "bundled.json", "pretty.json", "instrumented.json")},
            "calls": [{"index": phase["index"], "name": phase["name"], "strategy": phase["strategy"],
                       "before": phase["before"], "after": phase["after"],
                       "rng": [event for event in trace["rng"] if event["phaseIndex"] == phase["index"]]}
                      for phase in matches],
            "pythonAlgorithmsVerified": 0, "runtimeAccepted": False,
            "limitation": "Actual private source states only. Repeated strategy calls stay separate; V8 missing entries do not prove non-execution. No candidate values are used."}


def main(*, iteration="E05"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--stage", required=True, help="Actual processor class suffix, e.g. OrthogonalEdgeRouter")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    value = export(args.capture, args.request, args.stage, iteration=iteration)
    write(args.out, value)
    print("EXTRACTED_ACTUAL_PHASE_CALLS=" + str(len(value["calls"])))


if __name__ == "__main__":
    main()
