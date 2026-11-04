# E08 API and metadata source notice

The native facade and selected metadata descriptions are derived from the fixed
elkjs 0.12.1 distribution, npm gitHead
624ae90aa37110033a8af59c5ccbb292708b4317. Referenced files include lib/elk-api.js
and lib/elk-worker.js; the corresponding repository API/dispatcher source is
identified separately in references/e08-api-metadata-sources.json and
references/e08-execution-sources.json in the source repository.

Copyright (c) 2017 Kiel University and others. These source portions are offered
under EPL-2.0 OR GPL-3.0-or-later, subject to their original secondary-license
conditions. The complete upstream license accompanies this package as
elkjs-LICENSE.md. Earlier algorithm and numerical notices remain applicable.

The Python instance registry, bounded queue, thread/spawn scheduling, deadlines,
process cancellation and resource cleanup are explicit native host design under
ADR0007. They do not claim to implement the JavaScript FakeWorker terminate
behavior, and no JavaScript worker or reference metadata snapshot is executed
as a runtime fallback. The exact external Java build revision remains unresolved;
E08 does not broaden any algorithm-source approval.
