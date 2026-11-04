# py-elk

[中文](README.md) | English

A native Python graph layout engine targeting the public elkjs API and ELK JSON geometry,
with **elkjs 0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`** as its sole behavior baseline.
py-mermaid will replace its ELK backend with py-elk; there is no legacy ELK compatibility branch.

**Native Python implementation, version 0.1.0.** The default registry contains 12 providers, 243 options and 8 categories, including the complete Layered strategies across 196 Python modules. Differential, geometric, platform and installation reports retain their actual scopes; registry counts do not certify all inputs or option combinations. See the [current implementation status](docs/FULL_NATIVE_IMPLEMENTATION.md). Earlier bounded-slice limits describe historical acceptance. Runtime layout uses Python,
without Node, Java/JVM, browsers, JavaScript interpreters or a reference-engine fallback.
Callers provide measured label sizes. This package computes geometry and does not render.

The E09 experimental API accepts boolean `logging` and `measureExecutionTime`
arguments and records the actual processor monitor tree. Only root `logging` is
reserved; nested business fields remain intact. Generated `executionTime` retains
the fixed elkjs conversion: integer wall-millisecond delta times1000 times1e-9,
which must not be interpreted as conventional seconds or CPU time. See the
[example](examples/diagnostics.py) and [ADR0008](docs/decisions/0008-e09-diagnostics-coverage.md).
Current same-wheel acceptance remains recorded separately in release status.

The verified official default catalogue contains **12 algorithms, 243 options and 8 categories**.
These remain coverage denominators. Full native provider paths are callable; complete layout/option acceptance is pending unified validation.
The 64 indexed elkjs source files include 14 Mocha files; these are not assertion counts.
The exact external Java source commit behind the generated worker still requires an audit.
See the [source lock](UPSTREAM.json), [provenance](references/README.md) and [ledger](docs/compatibility.json).

The PyPI distribution is **`py-visactor-elk`**; the import remains **`pyelk`** and the GitHub repository remains `py-elk`.

```shell
python -m pip install py-visactor-elk==0.1.0
```

## Development

Run from the project root with CPython 3.11+ in a separate environment. These commands install
the current local package; consult release status for publication and download evidence.

```shell
python -m venv .venv
```

Activate the environment, then:

```shell
python -m pip install -e ".[dev]"
python scripts/iteration/implementation_interfaces.py --source-dir src --out test-runs/start-imports.json
python examples/show_scope.py
```

Use affected checks during development; reserve `scripts/check.py` for final full acceptance. Optional `scripts/upstream.py fetch/check` provenance checks require Git and network access for the first fetch. Node is used only by
the [development reference tool](tools/reference/README.md). Bootstrap success certifies no layout.
CI configuration targets Windows/Linux and Python 3.11–3.14; actual executed checks are listed separately.
Real official capture, full JSON comparison, flat geometry, determinism and negative controls
are available; see the [validation guide](docs/LAYOUT_VALIDATION.md). Saved observations and current native tests have separate scopes; a passing structural check does not certify complete algorithm or option semantics. Implementation is complete; final evidence closure and publication remain pending.

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

The current execution order is all feature implementation, unified validation and affected repairs, then standalone publication. Mermaid integration remains later. Detailed working documents are currently in Chinese:
[first stable release scope](docs/FIRST_RELEASE_SCOPE.md),
[startup](docs/NEW_SESSION.md), [complete plan](docs/IMPLEMENTATION_PLAN.md),
[work packages](docs/TASKS.md), [API contract](API_COMPATIBILITY.md),
[Python implementation strategy](docs/IMPLEMENTATION_PLAN.md#2a-python实现策略),
[concrete iterations](docs/ITERATION_PLAN.md), [machine progress index](docs/iteration-plan.json),
[parallel execution and retrospective protocol](docs/PARALLEL_EXECUTION.md),
[native comparison contract](docs/decisions/0001-native-contract.md),
[host foundations](docs/HOST_FOUNDATIONS.md),
[E07 retrospective](docs/retrospectives/E07.md), [E08 brief](docs/iterations/E08.md),
[testing/release](docs/TEST_AND_RELEASE.md), [current status](docs/RELEASE_STATUS.md),
[Mermaid integration](docs/MERMAID_INTEGRATION.md), [examples](examples/README.md).

The machine plan records completed iterations and the next brief; E07 extends the real chain to four directions, multiple components and the nine basic options.
The explicit native comparison profile retains raw strict differences. CPU layout runs in a spawned Python child process with one slot and a FIFO queue per instance. Cancellation, timeout and synchronous closure reclaim the worker. `max_pending=16` bounds running plus queued work (configurable from1 to64); optional `timeout` seconds cover queueing, startup and execution. No hard memory quota is promised. Three asynchronous metadata queries describe only the registered native subset and nine parsed options. Inputs remain independent; an idle instance can be reused across successive event loops. Logging/timing flags accept booleans; omission defaults to false and true records actual execution diagnostics. Standalone scripts use an `if __name__ == "__main__"` guard for spawn.

Upstream declares `EPL-2.0 OR GPL-3.0-or-later`; its [license text](references/licenses/elkjs-LICENSE.md)
is preserved. The project's own distribution license remains undecided, as in the original design.
The guarded E04–E07 kernel and E08 facade/metadata use pinned source portions and preserve their notices in the wheel. Native process scheduling is explicit Python host design. Resolve remaining [license/source release tasks](THIRD_PARTY_NOTICES.md) before formal publication.
