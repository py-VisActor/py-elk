"""Run real bounded native layout and inspect its source-defined monitor tree."""
import asyncio
import json

from pyelk import ELK


async def main():
    graph = {"id": "root", "children": [
        {"id": "a", "width": 30, "height": 20},
        {"id": "b", "width": 40, "height": 25}],
        "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]}],
        "business": {"executionTime": "caller-owned"}}
    elk = ELK()
    try:
        result = await elk.layout(graph, {"logging": True, "measureExecutionTime": True})
        print(json.dumps(result["logging"], ensure_ascii=False, indent=2))
        # executionTime retains fixed elkjs's generated wall-tick scale:
        # float(delta_integer_milliseconds * 1000) * 1e-9, not CPU seconds.
        assert "logging" not in graph
        assert result["business"] == graph["business"]
    finally:
        elk.terminateWorker()


if __name__ == "__main__":
    asyncio.run(main())
