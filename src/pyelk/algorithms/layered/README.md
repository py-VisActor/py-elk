# Layered implementation boundary

The current E07 guarded native slice implements import/export, GREEDY cycle
breaking, NETWORK_SIMPLEX ranks, long-edge splitting/joining, both default
LayerSweep passes, Brandes/Koepf placement and normalized orthogonal routing.
Real direction PRE/POST processors support RIGHT/LEFT/DOWN/UP and default.
Source component DFS, stable SimpleRow packing, unsplit false mode and the
NS private component driver retain their actual ordering and shared RNG.
Four self-loop stages extend19 ordinary calls to23; nonRIGHT adds two calls.
Admission covers0–8 total original nodes, at most28 edges, arbitrary weak
components and given dimensions within the reviewed numeric domain.
Parallel edges retain independent original objects and ports.

Phase order, identities, model order, primitive random consumption and floating
operations follow the fixed generated elkjs0.12.1 source. Full closure is in
references/e07-component-approvals.json (33 components); behavior is tested separately. No
reference files, Node/JVM backend or saved coordinates are read at runtime.
Explicit ports/labels, compound graphs and other strategies remain outside
this scope. See docs/E07_DIRECTIONS_COMPONENTS.md and RELEASE_STATUS.md.
