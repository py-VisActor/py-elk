"""Adapter for the future real pyelk ELK API. Missing API is a harness failure.

Protocol: python run_pyelk_candidate.py REQUEST_JSON NEW_OBSERVATION_JSON
Use the chosen Python environment (e.g. an isolated installed wheel). No sys.path
injection, golden reads, JS fallback or stand-in layout implementation is allowed.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import inspect
import json
from pathlib import Path
import platform
import sys
import traceback


async def main():
    request_path, output_path = map(Path, sys.argv[1:])
    # Import failure must not look like a valid ELK error-contract observation.
    import pyelk
    from pyelk import ELK

    request_bytes = request_path.read_bytes()
    request = json.loads(request_bytes)
    graph = copy.deepcopy(request["graph"])
    options = copy.deepcopy(request["constructor"])
    args = copy.deepcopy(request["layoutArguments"])
    observation = {"schema": "py-elk-layout-observation/v1", "requestSha256": hashlib.sha256(request_bytes).hexdigest(),
                   "engine": {"name": "pyelk", "version": pyelk.__version__, "modulePath": str(Path(pyelk.__file__).resolve()),
                              "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                              "sourceSha256": {p.relative_to(Path(pyelk.__file__).parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in sorted(Path(pyelk.__file__).parent.rglob("*.py"))}}}
    elk = None
    try:
        elk = ELK(options)
        result = elk.layout(graph, args)
        observation["result"] = await result if inspect.isawaitable(result) else result
        observation["outcome"] = "returned"
    except Exception as error:
        observation.update(outcome="threw", error={"name": getattr(error, "name", type(error).__name__), "message": str(error)},
                           diagnostics={"errorStack": traceback.format_exc()})
    observation.update(inputAfter=graph, constructorAfter=options, argumentsAfter=args)
    if elk is not None:
        try:
            result = elk.terminateWorker()
            if inspect.isawaitable(result):
                await result
            observation["termination"] = {"outcome": "returned"}
        except Exception as error:
            observation["termination"] = {"outcome": "threw", "name": getattr(error, "name", type(error).__name__), "message": str(error)}
    else:
        observation["termination"] = {"outcome": "notConstructed"}
    with output_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(observation, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
