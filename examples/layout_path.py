"""Run the actual E04 path slice from an installed py-elk package."""
import asyncio
import json

from pyelk import ELK


async def main():
    elk = ELK()
    graph = {
        "id": "root",
        "children": [{"id": "a", "width": 40, "height": 30},
                     {"id": "b", "width": 30, "height": 20}],
        "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]}],
    }
    print(json.dumps(await elk.layout(graph), indent=2))
    elk.terminateWorker()


if __name__ == "__main__":
    asyncio.run(main())
