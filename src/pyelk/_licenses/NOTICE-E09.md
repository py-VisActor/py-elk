# E09 execution diagnostics source notice

The progress-monitor tree, logging collection, source-defined processor names,
Network simplex monitor boundaries, BK diagnostic messages and root logging
cleanup derive from the fixed elkjs 0.12.1 generated lib/elk-worker.js,
SHA256 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86,
npm gitHead 624ae90aa37110033a8af59c5ccbb292708b4317.

Copyright Kiel University and others. These portions retain the upstream
EPL-2.0 OR GPL-3.0-or-later terms and original secondary-license conditions.
The full upstream license is included as elkjs-LICENSE.md; all earlier
algorithm, numerical and API notices remain applicable.

The fixed generated distribution's integer wall-millisecond tick conversion
is preserved explicitly. It must not be described as CPU time or assumed to
use conventional seconds. Python acquisition of wall ticks, asynchronous
process scheduling and cancellation remain explicit native host choices.
No external Java build identity is claimed, and no JavaScript or other layout
backend is executed by this package.

Decimal rendering of live numeric log values is an original Python host
adaptation to the reference runtime's intrinsic Number presentation. It is
checked against independent reference formatting probes; no nonexistent
upstream formatter implementation is claimed as a mechanical source port.

The repository records exact guarded source spans, actual callers and
independent reviews in references/e09-diagnostics-sources.json and ADR0008.
Diagnostics observation does not enlarge the admitted graph/option domain.
