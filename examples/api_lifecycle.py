"""Query native capabilities and run a real layout with explicit cleanup.

Import an installed py-elk package, or set PYTHONPATH to src for a source check.
This example does not load reference data or change the import search path.
"""
import asyncio
import copy
import json

from pyelk import ELK


async def main():
    graph = {
        "id": "root",
        "children": [
            {"id": "a", "width": 40, "height": 30},
            {"id": "b", "width": 30, "height": 20},
        ],
        "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]}],
        "business": {"note": "Caller-owned data stays unchanged"},
    }
    original = copy.deepcopy(graph)
    elk = ELK({"algorithms": ["layered"]}, max_pending=2)
    try:
        algorithms = await elk.knownLayoutAlgorithms()
        options = await elk.knownLayoutOptions()
        categories = await elk.knownLayoutCategories()
        counts = {"algorithms": len(algorithms), "options": len(options), "categories": len(categories)}
        assert counts == {"algorithms": 1, "options": 9, "categories": 1}

        result = await elk.layout(graph)
        assert graph == original
        assert result["children"][0]["x"] < result["children"][1]["x"]
        assert result["business"] == original["business"]
        print(json.dumps({"metadataCounts": counts,
                          "algorithm": algorithms[0]["id"],
                          "inputPreserved": graph == original,
                          "tracePhases": len(elk.last_trace),
                          "result": result}, indent=2))
    finally:
        elk.terminateWorker()


if __name__ == "__main__":
    # Spawned workers import the main module. Guard execution to avoid creating
    # another parent instance while the child interpreter is starting.
    asyncio.run(main())
