# py-elk

[中文](https://github.com/py-VisActor/py-elk/blob/main/README.md) | English

Native Python graph layout: provide an ELK JSON graph and receive node, port,
and edge geometry. Use it for flowcharts, data-flow graphs and other automatic
layouts. Your application supplies text measurements and renders the result.

- Python 3.11+, with no third-party runtime dependencies.
- Async `ELK` API with an isolated Python layout worker.
- Layered, tree, radial, force-directed and packing algorithms.
- No Node.js, Java, browser or JavaScript engine required.

## Install

```shell
python -m pip install py-visactor-elk==0.1.1
```

The PyPI distribution is **`py-visactor-elk`**; the import is **`pyelk`**.

## Quick start

Save this as `layout_example.py`, then run `python layout_example.py`:

```python
import asyncio
from pyelk import ELK

async def main():
    graph = {
        "id": "root",
        "layoutOptions": {
            "elk.algorithm": "layered",
            "elk.direction": "RIGHT",
        },
        "children": [
            {"id": "a", "width": 40, "height": 30},
            {"id": "b", "width": 40, "height": 30},
        ],
        "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]}],
    }
    async with ELK(timeout=30) as elk:
        result = await elk.layout(graph)
        print(result["children"])
        print(result["edges"])

if __name__ == "__main__":
    asyncio.run(main())
```

Workers use `spawn`: keep the main guard and close the instance when finished.
`async with` handles cleanup; alternatively call `elk.close()` in `finally`.
The input graph is not modified. Results contain node positions and edge
sections/bend points.

## Algorithms and options

Set `elk.algorithm`, `elk.direction` and other values in `layoutOptions`.
Use `await elk.knownLayoutAlgorithms()`, `knownLayoutOptions()` and
`knownLayoutCategories()` to inspect the current instance's catalogue.
The default catalogue has 12 algorithms, 243 options and 8 categories; registration
counts do not certify every option combination. See the [user guide](https://github.com/py-VisActor/py-elk/blob/main/docs/USAGE.md)
for ports, measured labels and compound graphs.

## Documentation

- [User documentation](https://github.com/py-VisActor/py-elk/blob/main/docs/README.md): installation, usage, API and troubleshooting.
- [API index](https://github.com/py-VisActor/py-elk/blob/main/docs/API.md): arguments, lifecycle, queues, deadlines and errors.
- [Changelog](https://github.com/py-VisActor/py-elk/blob/main/CHANGELOG.md) and [third-party notices](https://github.com/py-VisActor/py-elk/blob/main/THIRD_PARTY_NOTICES.md).
- [Maintainer and AI agent guide](https://github.com/py-VisActor/py-elk/blob/main/docs/development/README.md).

The behavior baseline is fixed **elkjs 0.12.1**. The [compatibility contract](https://github.com/py-VisActor/py-elk/blob/main/API_COMPATIBILITY.md)
records host differences and finite verification boundaries. Arbitrary inputs
are not promised identical floating-point coordinates across implementations.

## License and feedback

Original code is MIT licensed. Ported sources retain applicable EPL-2.0 /
GPL-3.0-or-later and Apache-2.0 terms; see [LICENSE](https://github.com/py-VisActor/py-elk/blob/main/LICENSE) and
[THIRD_PARTY_NOTICES.md](https://github.com/py-VisActor/py-elk/blob/main/THIRD_PARTY_NOTICES.md).
Report issues at [GitHub Issues](https://github.com/py-VisActor/py-elk/issues).
