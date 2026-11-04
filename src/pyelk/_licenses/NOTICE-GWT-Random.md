# GWT Random helper attribution

The seeded `JavaRandom` helper and its signed arithmetic support in
`pyelk/algorithms/layered/phases.py` are Python adaptations of the fixed generated
`java.util.Random` helper in elkjs 0.12.1 `lib/elk-worker.js`, lines 17014-17097.
The fixed worker SHA256 is
275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86;
the reviewed seeded subset is recorded in the source repository at
`references/e04-source-components-B.json`, component
`support:generated-JavaRandom`. The Python adaptation changes representation to
a native 48-bit integer state, adds explicit input checks and diagnostic draw
counts, and preserves the reviewed generated draw and arithmetic semantics.
The unseeded constructor and Gaussian generation are not included.

The corresponding emulated Random source in the GWT 2.13.0 tag bears the
following attribution, retained for these adapted helper portions:

Copyright 2009 Google Inc.

Licensed to the Apache Software Foundation (ASF) under one or more contributor
license agreements. See the NOTICE file distributed with this work for additional
information regarding copyright ownership. The ASF licenses this file to You
under the Apache License, Version 2.0.

INCLUDES MODIFICATIONS BY RICHARD ZSCHECH AS WELL AS GOOGLE.

These helper portions are licensed under the Apache License, Version 2.0.
The complete license, including its disclaimer of warranties and limitations of
liability, accompanies this package in `Apache-2.0.txt`:
https://www.apache.org/licenses/LICENSE-2.0

GWT comparison source:
https://github.com/gwtproject/gwt/blob/2.13.0/user/super/com/google/gwt/emul/java/util/Random.java

Its original bytes have SHA256
f9a862bd85bcac2039f030480820b497666f471060555c6d739dd160aaae5cd9.
The fixed elkjs build declaration names GWT 2.13.0, but that declaration and this
matching candidate source do not prove the exact worker compilation inputs.
The exact external Java/GWT build identity remains unresolved. No complete
GWT/Guava runtime is bundled. This notice supplements the existing ELK notices;
it does not replace their licenses or choose a license for original project
host code.
