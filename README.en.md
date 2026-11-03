# py-elk

[中文](README.md) | English

A native Python graph layout engine targeting the public elkjs API and ELK JSON geometry,
with **elkjs 0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`** as its sole behavior baseline.
py-mermaid will replace its ELK backend with py-elk; there is no legacy ELK compatibility branch.

**Bootstrap, planning and validation tooling.** The package exposes version metadata; there is no `ELK`/`layout`
API, implemented algorithm or published Python distribution. Runtime layout will use Python,
without Node, Java/JVM, browsers, JavaScript interpreters or a reference-engine fallback.
Callers provide measured label sizes. This package computes geometry and does not render.

The verified official default catalogue contains **12 algorithms, 243 options and 8 categories**.
These remain coverage denominators, with all Python capabilities unimplemented.
The 64 indexed elkjs source files include 14 Mocha files; these are not assertion counts.
The exact external Java source commit behind the generated worker still requires an audit.
See the [source lock](UPSTREAM.json), [provenance](references/README.md) and [ledger](docs/compatibility.json).

## Development

Run from the project root with CPython 3.11+ in a separate environment. These commands install
a local development scaffold, not a released layout product.

```shell
python -m venv .venv
```

Activate the environment, then:

```shell
python -m pip install -e ".[dev]"
python scripts/check.py --out test-runs/start-01
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py fetch
python scripts/upstream.py check
python examples/show_scope.py
```

Provenance checks require Git and network access for the first fetch. Node is used only by
the [development reference tool](tools/reference/README.md). Bootstrap success certifies no layout.
CI configuration targets Windows/Linux and Python 3.11–3.14; actual executed checks are listed separately.
Real official capture, full JSON comparison, flat geometry, determinism and negative controls
are available; see the [validation guide](docs/LAYOUT_VALIDATION.md). These certify no Python algorithm.

## Roadmap and entry points

| Stage | Deliverable |
| --- | --- |
| M0 | Structure, source/metadata lock, coverage ledger, checks and local scaffold packaging |
| M1 | Source/license mapping, assertion inventory, JSON/options/API contracts and complete oracle |
| M2 | Actual flat layered pipeline and full numerical differences |
| M3 | Close the basic input/options/API/error and coordinate contract |
| M4 | Standalone candidate packaging, platforms, lifecycle/limits and real layout installation |
| M5 | Publish the first real stable Python package, planned version 0.1.0, and verify downloads |
| M6 | Advanced ports/labels/hierarchy and complete layered strategies/options |
| M7 | The other eleven algorithms, each independently verified |
| M8 | Full conformance, reliability and subsequent stable releases |
| I0–I3 | Separate later py-mermaid integration using a published py-elk version |

Detailed working documents are currently in Chinese:
[first stable release scope](docs/FIRST_RELEASE_SCOPE.md),
[startup](docs/NEW_SESSION.md), [complete plan](docs/IMPLEMENTATION_PLAN.md),
[work packages](docs/TASKS.md), [API contract](API_COMPATIBILITY.md),
[Python implementation strategy](docs/IMPLEMENTATION_PLAN.md#2a-python实现策略),
[concrete iterations](docs/ITERATION_PLAN.md), [machine progress index](docs/iteration-plan.json),
[testing/release](docs/TEST_AND_RELEASE.md), [current status](docs/RELEASE_STATUS.md),
[Mermaid integration](docs/MERMAID_INTEGRATION.md), [examples](examples/README.md).

Upstream declares `EPL-2.0 OR GPL-3.0-or-later`; its [license text](references/licenses/elkjs-LICENSE.md)
is preserved. The project's own distribution license remains undecided, as in the original design.
No algorithm source has been ported. Resolve the [license/source release tasks](THIRD_PARTY_NOTICES.md)
before any external distribution; do not publish this scaffold as a usable layout package.
