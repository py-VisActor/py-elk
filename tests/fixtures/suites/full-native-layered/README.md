# Full native Layered public API matrix

`cases.json` contains 72 immutable requests. Each request goes through public
`ELK(...).layout(graph, arguments)` on the locked stock elkjs package and the
candidate Python package. Graph, node, port, edge and label business fields are
included. Given dimensions are supplied; no text measurement is inferred.

The runner is `scripts/validate_full_layered.py`. Inspect inputs without layouts:

```powershell
python scripts/validate_full_layered.py --check-inputs
```

Execute after a complete implementation freeze:

```powershell
python scripts/validate_full_layered.py --run --source src --node "C:/Program Files/nodejs/node.exe" --out test-runs/full-layered-new
```

Use repeated `--case ID` arguments to run only a changed feature group. The
reference collector batches selected requests in one Node process, with a
fresh stock ELK instance per request. Candidate subprocesses use Python `-I`,
empty PATH and the explicit source directory (or the installed package when
`--source` is omitted). Raw observations, argv, stdout, stderr, errors and
unprojected differences are retained. Source hashes are recorded before and
after each candidate call.

Successful comparisons check complete result JSON including logging and all
business fields, constructor/argument/input preservation and termination.
The existing explicit ADR0011 generated shape-cache projection is recorded
separately from the raw strict comparison. Timing is false for deterministic
JSON comparison. Source exceptions are retained as `reference-error-requires-review`,
never converted into passing coordinate tests.

Coverage includes four directions; all five explicit port constraints and four
sides; anchors, indices and offsets; node/port/center/end labels; compound and
cross-hierarchy transfer; nested external ports; loop distribution and ordering;
partitions; all promotion strategies; high-degree treatment; unzipping;
single/multi-edge wrapping; all horizontal compaction strategies and both
constraint calculators; disconnected packing; comments; all P3/P4 strategies;
semi-interactive constraints; feedback cycles; hypernodes; ID generation;
base spacing; flexibility/recomputation; and forced model order.

This is an integration matrix, not exhaustive coverage of every internal
branch or option cross-product. B's unified matrix owns P1/P2 strategy and
other algorithm coverage. Historical evidence remains separate: E13 source
catalogues, original object fixtures in `tests/fixtures/suites/next-native`, and the
HOST15–18 whole-call receipts refer to their original source versions, not
the promoted candidate. New results are stored under the selected output path.

The first unified execution is summarized in
`test-runs/20261104-HOST-19/A/full-layered-summary-01.json`: 66 returned stock
cases matched; six stock errors remain recorded. Logging-false variations
were added only for affected high-degree/unzipper paths, ARD for the stock
nonconstructible manual-cut property, and a nested external-port graph with
an actual parent. The first failed/raw observations were not rewritten.
