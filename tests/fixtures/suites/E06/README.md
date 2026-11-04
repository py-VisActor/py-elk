# E06 multigraph inputs and official reference

The suite keeps the complete 25-case master denominator. Fifteen original
requests are copied byte for byte, ten have explicit exclusion reasons, and
37 independent project requests cover directed rings/cycles, self-loops,
parallel edges, mixtures, edge/node permutations, nonzero seeds, zero/fractional
sizes and the 28-edge boundary. The long-edge pressure request produces 134
internal nodes in the official engine. Original E04/E05 suites remain separate.

`selection.json` preserves its input-preparation status. Current source approval
is recorded separately in `references/e06-component-approvals.json`; the
preparation record does not certify a Python implementation or full algorithm.
The reviewed domain is bounded to 0–8 original nodes, 28 total original edges
including loops/repeats, and the defaults and numeric limits in ADR-0005.

`oracle/` contains all 679 files of the genuine pinned elkjs 0.12.1 capture:
52 original requests, three fresh processes per request, observations, commands,
exit codes, stdout/stderr and fingerprints. `oracle-provenance.json` binds these
156 observations to the exact input and tool bytes. It contains no Python
candidate output. Input construction preceded E06 native admission; the final
geometry-policy recapture followed source review and never used candidate
coordinates as expected values. Cleanup errors remain raw observations and
establish no worker lifecycle compatibility.

All reference runs passed geometry and exact-repeat checks. Absolute 1e-6 and
relative 1e-9 tolerances remain unchanged. The earlier zero-size ring failure
is retained in the development run history. Only the explicit
`rankSeparation=default-greedy-simple-ring-v1` policy uses the reviewed GREEDY
GR-G6/NETWORK_SIMPLEX NS6-G7 proof: the **original** connected directed simple
ring has one incoming and outgoing edge per node and no extra edge or loop.
Zero coordinates cannot establish equal rank in that case. General cyclic
graphs receive no such exemption; overlap, route and root bounds still apply.

From the repository root, using Python 3.11+:

```shell
python scripts/build_e06_suite.py check
python -m unittest discover -s tests/validation -p test_e06_suite.py -v
python scripts/validate_e06_source_bindings.py --require-approved
python -m unittest discover -s tests/audit -p test_e06_source_bindings.py -v
python -m unittest discover -s tests/conformance -p test_e06_native.py -v
```

These checks work without Node or an ignored upstream checkout. Source checks
validate fixed identities, all 27 components, explicit independent reviews,
shared proof/dependency seals and the complete E05 review history. They do not
automatically prove mathematical equivalence or runtime acceptance. To recheck
actual Git/npm bytes, LF spans, UTF16 functions and lexical callsites, first
prepare the pinned development artifacts according to the project setup, then:

```shell
python scripts/validate_e06_source_bindings.py --with-upstream --require-approved --out test-runs/NEW-E06-source.json
python scripts/build_e06_suite.py build --out test-runs/NEW-E06-inputs
python scripts/validate_layout.py reference --cases test-runs/NEW-E06-inputs/cases.json --repeat 3 --out test-runs/NEW-E06-oracle
```

Every output path must be new. The native conformance tests call the real public
Python API against the same request bytes. They separately require the frozen
`native-basic-layered-v1` contract, input preservation, independent geometry,
exact repeats, original node/edge/section identities and ordered 19/23-stage
traces. Hidden self-loop holders remain in the identity denominator; dummy
chains must recover every original edge and endpoint. Only existing finite
integer reference shape `$H` adaptations are permitted. Nested business `$H`,
`error.stack` and public IDs remain exact. Deliberately omitted restorers and
synthetic coordinate/endpoint mutations are rejection controls, not additional
successful layout cases. Installed-wheel and cross-environment receipts are
recorded separately by the iteration audit.
