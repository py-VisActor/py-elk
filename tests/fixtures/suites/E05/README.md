# E05 proposed DAG inputs and genuine official oracle

This preparation suite registers all 25 original master cases. Twelve are copied
without reserializing their bytes; thirteen have explicit exclusion reasons.
Twenty-four separate project inputs explore connected flat DAGs with 2–8 nodes,
fork/join/diamond, multiple sources/sinks, multiple long edges, array permutations,
zero/fractional sizes, option precedence and fixed/default nonzero seeds.

The scope is `PROPOSED_SOURCE_GUARDS_PENDING`. Input membership does not establish
E05 source approval or Python support. The E04 suite and its raw captures remain
separate regressions. Numeric/node bounds and any additional processor guard must
be reviewed before freezing the E05 supported domain.

`oracle/` preserves the complete genuine pinned elkjs capture from
`test-runs/20261103-E05-01/V/oracle-proposed-first`: 36 requests, two independent
processes each, original command/exit/stdout/stderr records and SHA fingerprints.
`oracle-provenance.json` binds the snapshot to original inputs and capture tools.
The observations all returned and passed the existing geometry and exact-repeat
checks. Cleanup errors remain original facts and establish no worker lifecycle
compatibility. No native E05 candidate result is embedded.

From the repository root, Python 3.11+:

```shell
python scripts/build_e05_suite.py check
python -m unittest discover -s tests/validation -p test_e05_suite.py -v
python -m unittest discover -s tests/conformance -p test_e05_native.py -v
```

The conformance file initially checks official observations and explicitly named
synthetic comparer controls. Those controls confirm that DAGs need no expansion
of the existing finite-integer shape `$H`/input-preservation rules; they do not
claim a Python execution. Business `$H`, `error.stack`, section IDs, original
node/edge order and denominators remain exact. Geometry uses unchanged absolute
1e-6/relative 1e-9 tolerances; fresh process determinism remains exact.

Generate independent review material into a new directory and capture genuine
oracles separately. Neither command overwrites existing output:

```shell
python scripts/build_e05_suite.py build --out test-runs/NEW-E05-inputs
python scripts/validate_layout.py reference --cases test-runs/NEW-E05-inputs/cases.json --repeat 2 --out test-runs/NEW-E05-oracle
```

The official capture needs the verified development-only npm artifact and Node.
The versioned fixture checks are offline. Future Python acceptance must run the
real implementation against the same input bytes, retain strict raw differences,
and additionally verify stage ordering/adjacency, long-edge dummy chains and
original identity restoration under the approved source protocol.
