# Upstream notices for generated ELK source inputs

The E04 porting inputs are the generated `lib/elk-worker.js` distributed with
elkjs 0.12.1 and tracked at elkjs commit
`624ae90aa37110033a8af59c5ccbb292708b4317`.
Its SHA256 is `275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`.

The locked upstream package declares `EPL-2.0 OR GPL-3.0-or-later`. Its original
LICENSE.md is reproduced byte for byte as `elkjs-LICENSE.md` beside this notice.
This notice preserves that upstream declaration; it does not select the license
of unrelated py-elk host code or certify that the project is ready to publish.

The mechanical-port files must retain the upstream SPDX declaration and identify
their generated source. Their component/helper/condition mappings are recorded
in the development references `e04-source-components-A.json` and
`e04-source-components-B.json`; implementation acceptance is recorded separately.
Those development records, JavaScript engines and oracle outputs are not runtime
dependencies and are not bundled as executable backends.

The exact external Java checkout used to build the generated worker remains
unresolved. A candidate Java tag is explanatory material and is not represented
as that exact source identity. The locked generated worker is the porting source.
