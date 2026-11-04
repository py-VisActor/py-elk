# GWT port-list sorting helper attribution

The `_source_sort` helper in `pyelk/algorithms/layered/ports.py` is a Python
adaptation of the fixed generated comparator insertion/merge sort used by
elkjs 0.12.1 `lib/elk-worker.js`. Its fixed worker SHA256 is
275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
The actual source call chain is `$sort` (14192-14194), `sort_4` (14523-14526),
`mergeSort` (14495-14500), `mergeSort_0` (14502-14521),
`insertionSort` (14476-14485) and `merge_1` (14487-14493).

Copyright 2008 Google Inc.

The applicable source portions are licensed under the Apache License,
Version 2.0. A complete copy accompanies this package as `Apache-2.0.txt`:
https://www.apache.org/licenses/LICENSE-2.0

The Python adaptation uses native lists and valid internal object identities
instead of GWT runtime array/type scaffolding. It retains the observed
insertion threshold, alternating buffers, comparison order, copy shortcut and
left-on-equal merge behavior. Its scope is the complete port list and a supplied
comparator; it does not implement the complete Arrays library or natural-order
sorting. This file prominently records those changes to the original form.

The corresponding GWT 2.13.0 Arrays source carries the attribution above:
https://github.com/gwtproject/gwt/blob/2.13.0/user/super/com/google/gwt/emul/java/util/Arrays.java
Its original bytes have SHA256
6fec3efe98551cc5fae7c16cc5a447e63f10176815d769c2c465c2311e896e92.
That tag is comparison material, not proof of the exact worker compilation
inputs; the exact external Java/GWT build identity remains unresolved.

The separate `double_compare` implementation is an original Python IEEE
bit-order adapter to the observed scalar ordering. No generated GWT Double
implementation is copied. The ELK-derived port algorithms retain the applicable
ELK notices. This attribution supplements those notices and does not choose
the license for original project code or announce a released ports capability.

## Stress comparator PriorityQueue support

The `_PriorityQueue` support class in `pyelk/algorithms/stress.py` adapts the
fixed worker's GWT comparator heap used by Stress Dijkstra. Source block S08
and its independent source review preserve the actual offer, poll and removal
behavior, including downward-only repair with the mutable comparator.

Copyright 2008 Google Inc. These support portions use Apache License 2.0;
the complete text is included as `Apache-2.0.txt`. The adaptation stores native
Python object references in a list, takes the actual caller comparator and
omits GWT collection/type scaffolding. Equal keys retain the source comparison
schedule without an added stable counter. This records the modification from
the original form; it is not a general Java PriorityQueue/runtime port.
Stress algorithm portions separately retain their ELK dual-license notices.
The exact external GWT build identity remains unresolved.
