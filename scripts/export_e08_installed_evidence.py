"""Export actual sharing-protocol receipts only after fresh independent verification."""
import argparse
import base64
from pathlib import Path

from layout_checks import ROOT, load, sha256, write
from plan_suite_execution import identity_commands, verify_run
from validate_e08_runtime import INSTALLED, case_receipt, validate_layout_receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--api-receipt", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / INSTALLED)
    args = parser.parse_args()
    run = args.run.resolve()
    verified = verify_run(run)
    if not verified["passed"]:
        raise ValueError("Original actual run did not verify")
    names = ("report.json", "plan.json", "contexts.json", "objects.json", "suite-results.json", "installed-wheel.json")
    objects = load(run / "objects.json")["objects"]
    observations, commands = {}, {}
    for row in objects.values():
        observations[row["observationSha256"]] = base64.b64encode((run / row["observation"]).read_bytes()).decode("ascii")
        commands[row["commandReceiptSha256"]] = base64.b64encode((run / "objects" / row["executionKey"] / "command.json").read_bytes()).decode("ascii")
    for name in ("candidate-identity-command", "node-identity-command", "installed-wheel-command"):
        path = run / name / "command.json"
        commands[sha256(path)] = base64.b64encode(path.read_bytes()).decode("ascii")
    receipt = {"schema": "py-elk-e08-current-installed-evidence/v1", "runDirectory": run.relative_to(ROOT).as_posix(),
               "originalFilesSha256": {name: sha256(run / name) for name in names},
               "report": load(run / "report.json"), "plan": load(run / "plan.json"),
               "contexts": load(run / "contexts.json"), "objects": objects,
               "observationBytesBase64": observations, "commandBytesBase64": commands,
               "suites": {name: {"passed": view["passed"], "caseCount": view["caseCount"],
                                 "cases": [case_receipt(case) for case in view["cases"]]}
                          for name, view in load(run / "suite-results.json").items()},
               "installed": load(run / "installed-wheel.json"),
               "apiRuntime": load(args.api_receipt),
               "identityCommands": identity_commands(run), "runtimeReexecuted": False,
               "historicalExecutionAuthenticated": False, "pythonAlgorithmsVerified": 0, "packagePublished": False,
               "limitation": "Portable actual sharing-protocol commands, objects and independently evaluated case receipts; no fabricated legacy capture index, no historical authentication or new runtime execution by this exporter."}
    validate_layout_receipt(receipt, ROOT)
    write(args.out, receipt)
    print("E08_CURRENT_INSTALLED_EVIDENCE_EXPORTED")


if __name__ == "__main__":
    main()
