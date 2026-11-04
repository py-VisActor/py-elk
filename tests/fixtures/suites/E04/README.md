# E04 input suite and official oracle

This suite prepares the flat RIGHT/simple directed chain slice, including empty
and singleton graphs. It does not certify a Python layout implementation.

`selection.json` accounts for all 25 project-authored master cases: 5 are copied
byte-for-byte into `requests/master/`; 20 remain explicitly excluded. The 16
independent project inputs in `requests/project/` vary dimensions, zero sizes,
node/edge order, spacing, padding, option precedence and nonzero seeds. No input
contains expected coordinates. `cases.json` is the existing capture-suite schema.

The current preparation policy excludes other directions/topologies, advanced
shapes, element options, existing geometry, logging/timing, worker parameters,
zero seed and disabled component separation. It permits at most four children
and dimensions, spacing and padding no larger than 1,000,000. UNDEFINED direction
remains in the input; actual RIGHT output is checked against the official oracle.
Legacy element `properties`, edge `container`, unknown execution parameters and
algorithm filters other than an omitted filter or `['layered']` are also excluded.
Identical key names inside unrelated business data remain ordinary data.
Existing root `logging` and direct root/child `$H` fields are outside this
prototype because their reference cleanup/cache branches require separate work.
Nested business `$H`, `logging` and `error.stack` remain preserved inputs.
An explicit effective padding value must be a complete four-side string. E03's
object-valued padding convenience is outside this same-byte reference slice;
replaced constructor values and values overridden by local options stay ignored.

`oracle/` is an exact snapshot of the genuine pinned elkjs capture from
`test-runs/20261103-E04-01/V/oracle-first`, with 21 requests and 2 fresh-process
repetitions each. Raw observations, command exits and file fingerprints are kept.
`oracle-provenance.json` links the capture to input bytes and the locked package.
The capture predates the final numeric/node-count bounds; its original selection
hash and the revalidated current selection hash are both retained. All 21 request
bytes, case definitions and oracle observations stayed unchanged.
Observed repeated equality is limited to these samples. The snapshot itself
establishes no native Python acceptance. The independent conformance file also
executes the real public Python API against these 21 frozen inputs, checks input
and output isolation, and rejects deliberate removal of a required operation.
These source-tree tests do not establish installed-wheel or full-algorithm acceptance.

From the repository root, Python 3.11+:

```shell
python scripts/build_slice_suite.py check --suite tests/fixtures/suites/E04
python -m unittest discover -s tests/validation -p test_slice_suite.py -v
python -m unittest discover -s tests/conformance -p test_e04_cases.py -v
```

The source-binding checker is also available offline. Its canonical mode needs
the fixed local Git/npm artifacts, but no Node process:

```shell
python scripts/validate_e04_source_bindings.py
python scripts/validate_e04_source_bindings.py --with-upstream --out test-runs/NEW-E04-source.json
```

The offline result checks structure, explicit helper proof references, current
versioned approval/review links and notice fingerprints. Only canonical mode
checks actual source blobs, LF spans, UTF-16 function slices and lexical calls.
Neither mode automatically proves mathematical equivalence or executes a layout.

Build into a **new** directory to review regeneration; existing suites are never
overwritten:

```shell
python scripts/build_slice_suite.py build --out test-runs/NEW-E04-inputs
```

With Node and the verified local npm package, capture and strictly replay the
same suite. Both output paths must be new:

```shell
python scripts/validate_layout.py reference --cases tests/fixtures/suites/E04/cases.json --out test-runs/NEW-E04-reference --repeat 2
python scripts/validate_layout.py replay --reference tests/fixtures/suites/E04/oracle --candidate test-runs/NEW-E04-reference --out test-runs/NEW-E04-replay.json
```

Actual Python conformance must later use an installed real candidate and the
same `cases.json`, separately check geometry, exact repeated determinism and
input preservation, and retain strict raw differences alongside the explicit
native profile. No excluded master case is counted as a pass.
