# Internal option resolution

`resolve_options(constructor=..., layout_arguments=..., local=...)` parses the nine
core schemas defined in `OPTION_SPECS`. It first selects call `layoutOptions` when
present, otherwise constructor `defaultLayoutOptions`, then applies `local` values.
An explicit empty call mapping replaces constructor defaults. Outer `None` means
omitted; explicitly supplied option containers must be mappings.

`ResolvedOptions.values` and `origins` are read-only. `raw_values` returns copied
explicit source values. Canonical IDs and their `elk.` aliases are supported;
two aliases in one scope are ambiguous even when their values match. Bare suffixes
are rejected. The fixed 243-ID catalogue only distinguishes unknown names from
known options outside this parsing slice; it registers no executable algorithms.

Direction stays `UNDEFINED` by default. The algorithm schema declares `None`,
while a preferred canonical layered selection has origin `layout-fallback`.
That selection does not prove registration or execution. Seed zero is preserved
without inventing a deterministic random stream.

The explicit host value subset, source evidence and limitations are recorded in
`docs/decisions/0002-model-options-context.md` and
`references/e03-option-sources.json`. Runtime code reads neither file. There is
no layout, scheduler, lifecycle implementation or Java RNG in this module.
