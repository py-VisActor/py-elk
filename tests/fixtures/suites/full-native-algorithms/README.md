# Public API algorithm and strategy differential

`cases.json` contains 151 immutable requests: 12 algorithm baselines, the complete
9 cycle-breaking × 9 layering Cartesian product, 33 previously defined public
algorithm option requests, and all 25 original masters. These are public JSON
requests, not prepared internal phase objects. Each strategy-pair request has a
cycle, parallel edges, an isolated node, supplied sizes and positions, and a
fixed nonzero seed. All other Layered phases use their actual defaults.

Run from the repository root:

```text
python scripts/validate_full_algorithms.py --reference NEW_REFERENCE_DIRECTORY
python scripts/validate_full_algorithms.py --native-capture NEW_NATIVE_DIRECTORY
python scripts/validate_full_algorithms.py --compare REFERENCE/observations NATIVE/observations NEW_REPORT.json
```

The reference command executes one actual Node process for the entire suite,
verifies every fixed npm distribution file, and creates one public ELK instance
per request. The native command uses the formal `src/pyelk` public async ELK API,
including its actual process worker. Each native request has a 12-second API
deadline. Capture directories and reports must be new. For repairs, reuse the
unchanged reference and select only affected native requests with `--ids ID ...`.

Every result retains a raw strict difference. An additional comparison uses the
existing 1e-6 absolute / 1e-9 relative tolerances only at recognized geometry
paths. It separately lists a missing integer `$H` only where the original input
node/port had no such field. User `$H`, IDs, labels, arrays and business fields
remain mandatory. Original caller mutations and native caller preservation are
reported separately; the Python host preserves owned caller JSON.

`PASS` requires matching mandatory result fields, finite geometry and unchanged
native caller inputs. Runtime-generated hash differences remain visible even
for these cases. Source errors, unseeded random trajectories and source null
geometry have distinct observation statuses and do not count as layout PASS.
Error names/messages and termination results remain raw; Python host error
wrappers are not silently equated with JavaScript error strings. This suite does
not claim all 243 option combinations, lifecycle parity, distribution acceptance
or mathematical equivalence outside these requests.

The initial unified run is `test-runs/full-native-01/B`. Its original 151-case
capture is reused for saved-data comparison updates. Executed tool byte copies
are retained there; changes to a later checker do not rewrite its first report.
