# Scoped option effects and independent geometry

`cases.json` has 29 new public requests in two high priority port/label families;
`cases-02.json` adds four requests selecting actual external-label and nested-label
callers. Each stock request was captured once, and each native request ran through
the public API at version 0.1.0. Raw observations and commands remain in
`test-runs/full-native-closure/A/options-{reference,native}-0{1,2}`.

These are finite effects, not all values or combinations. All 33 full outputs
matched under the existing explicit generated-shape `$H` rule. Twenty distinct
options have actual geometry-change assertions. Ordinary port-label grouping
and node-label padding did not change the selected observables in some contexts;
their failed assertions remain failed. External WEST-port grouping did change
the actual label y coordinate. Node-label padding is not promoted to effect
coverage. An input option or copied output property is not an effect assertion.

The initial two insensitive pointer assertions and their failed report are
preserved. Only pure saved-data assertions were corrected to the actual changed
EAST-port label y and node-label x; no layout was replayed.

`cases-03.json` through `cases-07.json` add 45 actual public 0.1.0 calls for P3,
P4, routing, horizontal compaction, wrapping and high-degree parameters. All
45 complete returned results matched. Nineteen additional option IDs have
specific geometry effects; insensitive contexts remain failed attempts, including
node-influence weights, equal SCANLINE/QUADRATIC results and the tested tree-height
examples. This is not evidence those compiled options are unused. Earlier failed
node-only NS observations are preserved; the corrected pure observation includes
the actual moved port coordinates. No capture was replayed for that correction.

`geometry-saved/` contains six existing request/reference/native observations
and original command records, copied byte for byte. `geometry-frames/` contains
four existing coordinate-mode observations. Their manifests bind every copied
file. They support the independent geometry tests without Node, layout execution,
or an ignored workspace directory:

```shell
python -m unittest tests.validation.test_advanced_geometry -v
```

`protocol-saved/` contains five of the new actual 0.1.0 captures, including a
multi-pointer coordinate projection. It exercises
the effects checker and contrast assertions entirely offline:

```shell
python scripts/validate_option_effects.py --suite tests/fixtures/suites/full-option-effects/protocol-saved/cases.json --reference tests/fixtures/suites/full-option-effects/protocol-saved/reference --candidate tests/fixtures/suites/full-option-effects/protocol-saved/candidate --out test-runs/option-effects-pure-new.json
```

Independent geometry is deliberately scoped. The ordinary fixed-cardinal
leaf-node default anchor has a positive and corrupted-endpoint control. Unknown
FREE/external/hierarchical default anchors, general
label clearance, and guarantees absent from the selected layout are recorded as
`not_assessed`; a PARTIAL report never has `passed: true`. No non-overlap rule is
invented merely because a Source layout happened to avoid an overlap.
