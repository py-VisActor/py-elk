"""Offline fixed diagnostics sources and independent component approvals.

The canonical source spans and original review materials are embedded bytes.
Only --with-upstream reads local Git/npm caches. This gate approves bounded
observational source use, never runtime, full algorithm or release acceptance.
"""
from __future__ import annotations
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path

from layout_checks import ROOT, contained, load, sha256, write, _parse_json

SOURCES = "references/e09-diagnostics-sources.json"
APPROVALS = "references/e09-source-approvals.json"
COMMIT = "624ae90aa37110033a8af59c5ccbb292708b4317"
WORKER_SHA = "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86"
API_SHA = "ccca46175c05bbd280b5de6c9853103711e52c666a101f145b717e345363e24d"
JAVA_SHA = "8006b0bee9c363776699e08e71cb01de19a46e2ea8c79c93189d78098976761c"

# Literal seals of the fixed reviewed material, independent of edited manifests.
COMPONENT_SEALS = {'E09-D01-CLOCK': ['fixed-worker', 19, 19, '78cafc11589ae67ecf2eda16c799635da44f9826193a367c860ab5435fc9e4f6'],
 'E09-D02-LONG-ARITHMETIC': ['fixed-worker',
                             10682,
                             10794,
                             '3e463b8566a77063c20dc73c65938e58114eb9f940210a094105ce095b9bf96d'],
 'E09-D03-JSON-ROOT-CLEANUP': ['fixed-worker',
                               9864,
                               9882,
                               '4c58c18b43a80c853acaaddddcc8d51587762529a1614728dc526da4aea5ed84'],
 'E09-D04-BASIC-MONITOR': ['fixed-worker',
                           71989,
                           72152,
                           '41c2ba5f21895eb6913d39a38078122d9fbe66decb59963eb104ad42f09c593b'],
 'E09-D05-COLLECT': ['fixed-worker', 81766, 81800, '74fef78716d68c0ca11221deafaa74cd8ae845e8a1c1641b3c6d20777348d0a5'],
 'E09-D06-LAYOUT-ENTRY': ['fixed-worker',
                          81878,
                          81906,
                          '27c8aa28cb11d404ea24819dc223a2e94c8cf1caf4cb712bf3f4e9e8638f646d'],
 'E09-D07-RECURSIVE-ROOT': ['fixed-worker',
                            68487,
                            68528,
                            'ff81bd5a69655c73a651c50c14fcf42fd7027871ea213e563d8037e5fe4daedd'],
 'E09-D08-RECURSIVE-DISPATCH': ['fixed-worker',
                                68530,
                                68700,
                                'c3c91bbf90b5cae2d2b1a8c6c5f1553a478f6f21c6ad8de1c15345587073dbf8'],
 'E09-D09-LAYERED-COMPONENTS': ['fixed-worker',
                                28205,
                                28230,
                                '50d6df531c7de3116de5e97d00501694cfd43e1fcd894c830ccf636830f177ce'],
 'E09-D10-LAYERED-PHASES': ['fixed-worker',
                            28277,
                            28313,
                            '81aa69a4705ca8d2833a3a3fd8bf4a11ebf5fffbc3b0cb1106fe438c61d0450a'],
 'E09-D11-NETWORK-SIMPLEX-MONITORS': ['fixed-worker',
                                      52044,
                                      52089,
                                      '9374ccc601ee23121af9752aa8ab624cd32f2196e6a434451c6b12f20ab69d36'],
 'E09-D12-NETWORK-SIMPLEX-LEAF': ['fixed-worker',
                                  21366,
                                  21407,
                                  'efaa27cc6d609f8c955aa6e10f5d948f18e4fc2a021e5ed76cf1800220f25c2e'],
 'E09-D13-BK-MAIN': ['fixed-worker', 57564, 57664, '4b56227367acfffd52494fecde193193b8302bbec04beb10ce41b67d7dba668b'],
 'E09-D14-BK-FEASIBILITY': ['fixed-worker',
                            57435,
                            57462,
                            '73a433c432ec9f2f38ad6ff59b77218e049afd1cfcce556f5a26243508505f41'],
 'E09-D15-BK-MAPS': ['fixed-worker', 57666, 57707, 'f54c237451cecb2729f1f1c6029899ec3f838f9325a70f52d5c36d5b0312dfdf'],
 'E09-D16-BK-NUMBER-LABEL': ['fixed-worker',
                             57040,
                             57096,
                             '86a4e034f26b60355e2abef19fd16dcce00f8556619277fc5e4596bbac063bd5'],
 'E09-D17-NODE-IDENTITY': ['fixed-worker',
                           31940,
                           31949,
                           'b37d154f0ca48907ea44de9496cea6092fe7a3e7bdc2f9ba62ae7ddde6104270'],
 'E09-D18-NODE-DESIGNATION': ['fixed-worker',
                              33236,
                              33247,
                              'f9351ef53848a201aede74d21b99af4cc783994839f80fefee03bf3562224b63'],
 'E09-D19-NODE-STRING': ['fixed-worker',
                         33369,
                         33377,
                         '6eceb5cef56cb57c17dea13f052e222f53ea54e5b089a0b66d9f814e50c40643'],
 'E09-D20-ORIGIN-IDENTIFIER': ['fixed-worker',
                               34803,
                               34825,
                               '92dbf06840e16c03569d220661668d37d3af8e42b5d694295af2d1b44ac927c6'],
 'E09-D21-EDGE-STRING': ['fixed-worker',
                         32030,
                         32048,
                         'cb5f29be81a68a002737652bcc22a5776aa24cfd933f81fddc33fd6bc8409e7e'],
 'E09-D22-CLASS-NAME': ['fixed-worker', 257, 272, '225fb2665c3e836f5988fc8e5768abfa66ada5486fb35b45489691921c915960'],
 'E09-D23-DIRECTION-NAME': ['fixed-worker',
                            36556,
                            36567,
                            '5ccb9af2a9884952ab5d9e74b3c9e8e239ed8ec4daee64e3f254cd33a8032c97'],
 'E09-D24-MARK-CONFLICTS': ['fixed-worker',
                            57524,
                            57561,
                            '2e42b6cbd4f1188e0723a259aa5e7cbf59626d3619ee2b04c458f4f7ce57e795'],
 'E09-D25-HASHSET': ['fixed-worker', 15910, 15973, '0fc4bcaad45ff5be3ab804c778c22555fb275e93b437db1ae93c6e7ad9bab0bf'],
 'E09-D26-HASHCODE': ['fixed-worker', 15884, 15910, '1e2676a8acf19ddafaaebaa0a5e44a9800c4401aef69e83b681a2e96b62289a4'],
 'E09-D27-HASHMAP-ROUTING': ['fixed-worker',
                             13226,
                             13245,
                             'fa1fe8e55e8bdcfc5c8e40a775d28c3c0d82e559d8bb133a7decd0d85eec7b2e'],
 'E09-D28-MAP-ENTRY-ITERATOR': ['fixed-worker',
                                13330,
                                13381,
                                '09498c3e2bf48c3df41ce77abfa64c008fcbe879d66e26b5d24fbf2d2e768371'],
 'E09-D29-INTERNAL-MAP': ['fixed-worker',
                          16018,
                          16106,
                          '8e39921df604ab36a564b35888ff7514090cfd4140dd15be670997c334b65f0a'],
 'E09-D30-OBJECT-HASH': ['fixed-worker', 131, 147, '32e93750fb9489026025080cb7dc7d11b57aafa5be54948f4e1bf20ab610b72b'],
 'E09-D31-IDENTITY-HASH': ['fixed-worker',
                           19742,
                           19746,
                           'b57c7695e6929b895f62a548090eed55880f05a1eaecf77cacd8cd9c4e7677f8'],
 'E09-D32-MAP-STRING': ['fixed-worker', 1260, 1272, 'f27992e2ae2f7b144f0aec05ee9c8c2b108818f1242471af5771ec53333b088b'],
 'E09-D33-COLLECTION-STRING': ['fixed-worker',
                               1569,
                               1577,
                               'bbdabee0f557834476bb037972851f057798835c1e90631aa31837f277033ab9'],
 'E09-D34-PORT-DESIGNATION': ['fixed-worker',
                              33477,
                              33488,
                              'f2f8515f711a1dc023b9f11b3a916e77421cdd227fea7afc733208b11fe0e322'],
 'E09-D35-EDGE-DESIGNATION': ['fixed-worker',
                              31952,
                              31957,
                              'b1ecfde8cf334e64c59920dd8f3154dd8ca056a1164aa4a7aa6194c2f07dfdc3'],
 'E09-D36-STRING-BRIDGE': ['fixed-worker', 65, 70, 'c02d7896e23030165b9af7a97afba774cf1ee5de884affdfb412656cea7b6289'],
 'E09-D37-OBJECT-STRING': ['fixed-worker',
                           161,
                           164,
                           '9dda00ef489e594756903789c06ebf1914d1807c1c8d4605e4bf17559159619f'],
 'E09-D38-KEY-VIEW': ['fixed-worker', 13509, 13557, 'fd7a6ae92a44b6c3ea03a0f3953fc0fc970a99f2d3474b95947a2ecac3a3d0e0'],
 'E09-D39-NUMBER-CONCAT': ['fixed-worker',
                           57614,
                           57620,
                           '4af3ceb10a538afb6cd6be99153d244dc97095f85621fc98c97d7a07c4c9637f']}


COMPONENT_SEALS['E09-D40-PROVIDER-BOUNDARY'] = ['fixed-worker', 28532, 28544, 'a2869cfa17ace29cf3190c2b42f54b7add0ab95a35e1c4862dcd0152c4c13750']

BRANCH_MATRIX = "references/e09-branch-matrix.json"
REQUIRED_DECLARATIONS = {'api-registry': [4, 'api', 'bcb2410c4dec8199454e30bdc563e0982acefa40e8b82b4559ede647f3f72110'],
 'api-metadata': [5, 'api', '28c8a73ec12031d686c88e37849a0e3698f116cf9a07ba7f9881d65768820017'],
 'api-algorithm-errors': [5, 'api', '6252238bfdc8fa329b3f8d5061bb944d865b8026ffa83ea0fd6fab15d0cd43a4'],
 'api-closed': [3, 'api', 'c3bf4e9c26e25d7d4b80c561896a05c0fa325a70de87acf18bcafe2cd6a58877'],
 'api-worker-options': [2, 'api', '34d8d7ea5ed4a812e6284d5d97f1d87ba7f0cd0350fcf02b6ba9a4a5c3602936'],
 'option-algorithm': [5, 'geometry', 'd21ea6592e05328d6cb6558f27a74cd1e5304fa9e977c19bfe5385f44ba936eb'],
 'option-direction': [5, 'geometry', 'ccda38a1a0a4213b4957d94469c91a82a34e9992c2f889c450d471cee56b8e1b'],
 'option-padding': [5, 'geometry', 'd64d9392fc5ebda73205d421b47d117752ece79b7e39f9ff39cc2b0385a0ff2a'],
 'option-spacing.nodeNode': [5, 'geometry', 'f0fd74647f0977f5488683e5b7151822e484941eaf019caaaff6693e7756d4b0'],
 'option-layered.spacing.nodeNodeBetweenLayers': [5,
                                                  'geometry',
                                                  'b5b0f2c24e92facbee28a95fb97d123a291af76ac39a4d640766182acc09197e'],
 'option-separateConnectedComponents': [5,
                                        'geometry',
                                        '7965357ffb065bd7316c425e2094ff66a7c99fefb7c727bd8daa5b79f80db0ad'],
 'option-spacing.componentComponent': [5,
                                       'geometry',
                                       '623bd078d264d1efd0c8611769aabd9c7c37132e86e62db96699d514d9682241'],
 'option-edgeRouting': [5, 'geometry', 'c62e81c846af57abb9d0ba420bdc091e8822b774c5c543e677e9ed1e276fabae'],
 'option-randomSeed': [5, 'geometry', 'c3217420622577b59263a3cb8587db3707b09103f95611d4dd80d9c284cce835'],
 'option-scope': [6, 'geometry', 'f6a782ecf6a6965244dcf0994b400db31cec7f2018f5cc41fbaaf39ddb6a6dcd'],
 'domain-bounds': [11, 'newcoverage', '10257c4ef565fc6358cc12059bfec7c1f1949efdda74cfed817a76af0675b2e4'],
 'domain-topology': [12, 'geometry', '94e408e460de836192e7e77137632b88bc588d0bb4bdc7301f4ef54f3a2e880c'],
 'domain-directions': [5, 'geometry', '8891462592a2165cf9c3bebde3e95cdf149ea72c5b3692f57589b462274280df'],
 'domain-components': [5, 'geometry', '0e97a17db5221ea3e62fd347d09cc70746ef47fcf5bcffde073e12087e54a268'],
 'domain-rejections': [10, 'newcoverage', '078691eda98427a77e032f62a8fae8128572985e2037df97743f04689a26f0a7'],
 'domain-existing-geometry': [8, 'newcoverage', '92b33ca971729143f6cce4117d310a9a154e66185bb3e13572271ca810199dcb'],
 'domain-child-padding': [5, 'geometry', '982c4ef74836a9bde930e1e2f508cedbe8ad91245aeba7d4ad462e555f026fbf'],
 'diagnostic-flags': [6, 'newcoverage', 'cae40861f284273496a9be2db960d196304f9150608848e95ee0f852659a0062'],
 'diagnostic-root-cleanup': [7, 'newcoverage', '9509675b8602bf609e45391e3376527b54c28b923ab78cec2ff58dd0ce705d71'],
 'diagnostic-tree': [8, 'newcoverage', 'f8068eb639f122474ec19ad1b218ccfd38d49838e213f62a9c725dc843501e75'],
 'diagnostic-live-text': [9, 'newcoverage', 'e07e5a4eeb36df3ef3b62b9d70b89daf9928eee59e53fdb186617bb6031d1b54'],
 'diagnostic-number-adapter': [7, 'newcoverage', '60ecc89b9ab7c75a818bbd5502b63028a0555c0960d3f3aafb957a608941273c'],
 'diagnostic-identities': [5, 'newcoverage', '1b05b1f9d8925f2b271340d7bfc8d190e19779d6c8e4e90e56d68b9f4da69787'],
 'diagnostic-clock': [7, 'newcoverage', '0d8373f071fce1a70fb8f499cde1ff4277f62d270d2a656fc8247923f6482466'],
 'diagnostic-collect': [6, 'newcoverage', '79e849937a9367c8bd65e5fd1fd69b9ad2511d5918619100feba0e1c8d5c476c'],
 'diagnostic-monitor-state': [5, 'newcoverage', '89882e6da6e03d332705a8c3a32fcfbe96b28eddb62f5ed844e920106d8f5787'],
 'diagnostic-boundaries': [5, 'newcoverage', 'e2c098e8a3a93c031b5bd68e4231fa935cfcb05a386fc4c0496f091eca06ccf5'],
 'input-preservation': [6, 'geometry', '2b7795a1d0bf93c126f8121e6e14b03eca097ab9696d29019f1959f40c878720'],
 'lifecycle-fifo': [4, 'api', '168c883faf3798562554794cf5e106467348ca476a1d99d309f7a79435c4d11f'],
 'lifecycle-cancel-close': [5, 'api', '4574856895460dc356338695af3d7e2d4741acd8456c5cb89a8801574c1b2f2e'],
 'lifecycle-timeout': [4, 'api', 'e28951d8be24b8a20cc71d751ed0f86eb80a41e9a7768a3aa608cb6dd6ed90f9'],
 'lifecycle-loop-trace': [4, 'api', '75500b58e074eed46f698c97aaf4358f9eda4693b254e0780e8da38ac4d07ca0'],
 'lifecycle-errors': [5, 'api', '0402ac678aa3dfd597e35083bfc010a6da050560a556deb67e8c84d043954ac4']}
REQUIRED_PROFILE = {'id': 'basic-layered',
 'inputDomain': {'originalChildNodes': {'minimum': 0, 'maximum': 8},
                 'originalEdges': {'minimum': 0, 'maximum': 28},
                 'topology': 'flat-directed-multigraph',
                 'ids': 'nonempty strings',
                 'nodeDimensions': 'given finite nonnegative numbers, at most 1000000',
                 'spacingAndPaddingMaximum': 1000000,
                 'randomSeed': 'nonzero signed32; omitted defaults to 1',
                 'directions': ['UNDEFINED', 'RIGHT', 'LEFT', 'DOWN', 'UP'],
                 'preexistingGeometry': False,
                 'rootLogging': 'reserved; removed/replaced on returned copy',
                 'sourceDecision': 'docs/decisions/0008-e09-diagnostics-coverage.md'},
 'algorithm': 'org.eclipse.elk.layered',
 'optionIds': ['org.eclipse.elk.algorithm',
               'org.eclipse.elk.direction',
               'org.eclipse.elk.padding',
               'org.eclipse.elk.spacing.nodeNode',
               'org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers',
               'org.eclipse.elk.separateConnectedComponents',
               'org.eclipse.elk.spacing.componentComponent',
               'org.eclipse.elk.edgeRouting',
               'org.eclipse.elk.randomSeed'],
 'nativeRegistryCounts': {'algorithms': 1, 'options': 9, 'categories': 1},
 'fullReferenceCounts': {'algorithms': 12, 'options': 243, 'categories': 8}}
PLANNED_EVIDENCE = {'geometry': {'path': 'references/e09-installed-check.json',
              'pointer': '',
              'validator': 'validate_e08_runtime.validate_layout_receipt'},
 'api': {'path': 'references/e09-installed-check.json',
         'pointer': '/apiRuntime',
         'validator': 'validate_e08_api.validate_candidate_receipt'},
 'newcoverage': {'path': 'references/e09-coverage-installed.json',
                 'pointer': '',
                 'validator': 'validate_e09_coverage.validate_candidate_receipt'}}
MASTER_CASES = {'layered-empty': ['supported', '57e6af36d5003ea28ac539cc51f8f9e4d58813c84bbc1edb95e86a488c649dd6'],
 'layered-singleton': ['supported', '9d786993c385ce4418218b660cda677eb86601da9d809c4437e300c9bc85fa59'],
 'layered-chain': ['supported', '3747bbaf9deeb1497282539e35975a9a952176a326febf3128a99141f21838b4'],
 'layered-fork': ['supported', '3d263dbbf4469f6875b8a823bba26fc8c96bb2bcacf7bf129e9a196c5bcef41c'],
 'layered-join': ['supported', 'efc78c4c12913bc40a7d4ec7528832abfedc72a83716388f20d199a1fc890706'],
 'layered-diamond-right': ['supported', '5550f1ff7b77fd80dfe44d0a71b781ecc180f34ff69cd1eabbc525dbada4032e'],
 'layered-diamond-left': ['supported', '57b29520030aeff83f0fe9c6fe50c34beef63b4ef7770780138ec3e616a08cc1'],
 'layered-diamond-down': ['supported', '4328a7d279f44c3401ae81ec1f717a9eebd382725c1348f5b1f73562a6a44904'],
 'layered-diamond-up': ['supported', '27564c1ba565eb7a39264bedd56ff54db343a541d2ed718d21de9f6693128173'],
 'layered-long-edge': ['supported', '05b4e11fdb1dea49051ff02feef5749e657ab4ae2e0be1b08c5f31e1edac4464'],
 'layered-cycle': ['supported', 'b0c2b4592f68c7d12f62110f8a4e634d72f60d1b8610cc413ca96f3c7f59e3d3'],
 'layered-self-loop': ['supported', '6c6dbf7c47be7ebd810535c060636c3a34bbea750262ec87042a3425c53aab64'],
 'layered-parallel-edges': ['supported', 'c9dd965d28e40618e146473a5a657002dab902d552146bac74947e97ee316cfd'],
 'layered-disconnected': ['supported', '788d170145834f8b5bb2e6b4b220023c4b65b157aa61433cf84f67450a7931f4'],
 'layered-unequal-sizes': ['supported', '87569bf4ff068380347f1c5f3d62e6ad8c7c102fc9ddbf5aab91bd551f0287cf'],
 'layered-zero-size': ['supported', 'b9ee7eceb2d33ce8911da2e2c04223009e0317acaedfd1a35a6985fd0ec8ea23'],
 'layered-custom-spacing': ['supported', 'aeb9bd831f4ffa6f34ed52bbee90a19dcd25b564e8ad09c919b171030cc9b26a'],
 'layered-unseparated-components': ['supported', 'b422ef6e938addcc518202e4fab3c19cc9f6b5be4a029beb5309c9db3d248526'],
 'options-constructor-default': ['supported', 'ed8e56c9b4d8a45c6d97a966c5f480df7492dfd7e662e6ae7b02be3fcda3e421'],
 'options-explicit-empty-replaces-default': ['supported',
                                             'cc04bf06400f3b0e8824ce90b95e35396d48b2be7d8b3a66aa044ca3bb2aedde'],
 'options-call-replaces-default': ['supported', '952cf462958ac0aaaa4bf43f955bee5c18ff311e35a78325876e6dd7af213332'],
 'options-full-ids': ['supported', '1d4edfd7170d457870ad5799921326e3a418b20e901972eb671456912030eb5d'],
 'error-unknown-endpoint': ['expected-error', '4ff60bff8287784d5cd387df48e2f733efbbddf3d28c80e29f5ab55d517be4c6'],
 'error-unknown-algorithm': ['expected-error', '6776907f36ded445ddf2e736b0e2aa3bae46ca4712e4a26ef5ba443894370d28'],
 'error-missing-graph': ['expected-error', 'f62c50c6c515ff6c5f41af4da10e2dde9ebe0db474016a5b482603c73620afbb']}


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def raw_bytes(value):
    require(type(value) is str, "Source material encoding differs")
    return base64.b64decode(value, validate=True)


def fingerprint(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_source_facts(document, root=ROOT):
    root = Path(root)
    require(document["schema"] == "py-elk-e09-diagnostics-sources/v1", "Source schema differs")
    require(document["baseline"] == {"version": "0.12.1", "commit": COMMIT}, "Fixed source baseline differs")
    require(document["sourceApproved"] is True and document["sourceApprovalRecord"] == APPROVALS,
            "Limited source approval reference missing")
    require(type(document["pythonAlgorithmsVerified"]) is int and document["pythonAlgorithmsVerified"] == 0 and
            document["packagePublished"] is False, "Source facts promote runtime/release")
    sources = document["sources"]
    require(type(sources) is list and len(sources) == 3 and len({row["sourceId"] for row in sources}) == 3,
            "Source file denominator differs")
    registry = {row["sourceId"]: row for row in sources}
    require({key: row["sha256"] for key, row in registry.items()} ==
            {"fixed-worker": WORKER_SHA, "fixed-api": API_SHA, "readable-ElkJs": JAVA_SHA}, "Fixed source identity differs")
    require({key: row['path'] for key, row in registry.items()} == {
        'fixed-worker': 'lib/elk-worker.js', 'fixed-api': 'lib/elk-api.js',
        'readable-ElkJs': 'src/java/org/eclipse/elk/js/ElkJs.java'}, "Fixed source paths differ")
    for key, seal in {
        'fixed-api': [73, 94, 'ebda7e789b7394b519731bce569a74a2a26bf9c733132534c6330638d52c5751'],
        'readable-ElkJs': [171, 254, '79f4231b1d87353d857c0c456e505901c021caf1f5eca072b9222bfc34c0e262']}.items():
        require([registry[key]['startLine'], registry[key]['endLine'], registry[key]['spanSha256']] == seal,
                "Fixed auxiliary source span seal differs")
    lock = load(root / "UPSTREAM.json")
    require(lock["javascript"]["version"] == "0.12.1" and lock["javascript"]["commit"] == COMMIT and
            lock["distribution"]["sha256Files"]["lib/elk-worker.js"] == WORKER_SHA and
            lock["distribution"]["sha256Files"]["lib/elk-api.js"] == API_SHA, "Source/current lock baseline differs")
    for row in sources:
        if row["sourceId"] == "fixed-worker":
            continue
        raw = raw_bytes(row["sourceBytesBase64"])
        require(fingerprint(raw) == row["spanSha256"] and b"\r" not in raw and raw.endswith(b"\n"),
                "Auxiliary source span bytes differ")
        require(len(raw.decode("utf-8").splitlines()) == row["endLine"] - row["startLine"] + 1,
                "Auxiliary source span range differs")
        if row["sourceId"] == "readable-ElkJs":
            original = raw_bytes(row["originalFileBytesBase64"])
            require(fingerprint(original) == JAVA_SHA and row["commit"] == COMMIT, "Readable fixed Git bytes differ")
            actual = ("\n".join(original.decode("utf-8").splitlines()[row["startLine"] - 1:row["endLine"]]) + "\n").encode()
            require(raw == actual, "Readable source range differs from original Git bytes")
    components = document["components"]
    require(type(components) is list and len(components) == len(COMPONENT_SEALS) and
            len({row["componentId"] for row in components}) == len(components) and
            {row["componentId"] for row in components} == set(COMPONENT_SEALS), "Source component denominator differs")
    for row in components:
        expected = COMPONENT_SEALS[row["componentId"]]
        require([row["sourceId"], row["startLine"], row["endLine"], row["spanSha256"]] == expected,
                "Fixed source component seal differs")
        raw = raw_bytes(row["sourceBytesBase64"])
        require(fingerprint(raw) == expected[3] and b"\r" not in raw and raw.endswith(b"\n") and
                len(raw.decode("utf-8").splitlines()) == expected[2] - expected[1] + 1, "Original source span bytes/range differ")
        require(type(row["actualCaller"]) is str and bool(row["actualCaller"]) and
                type(row["approvedScopeProposal"]) is str and bool(row["approvedScopeProposal"]), "Source caller/guard evidence missing")
    clock = document["clockFacts"]
    require(type(clock["intern47"]) is int and clock["intern47"] == 1000 and clock["doneMultiplier"] == 1e-9 and
            clock["equivalentScalePerWallMillisecond"] == 1e-6 and clock["notCpuTime"] is True and
            clock["formula"] == "(end_ms*1000-start_ms*1000)*1e-9", "Generated wall-clock scale differs")
    intrinsic = document["numberConversionProvenance"]
    require(intrinsic["elkjsDedicatedFormatterSourceAvailable"] is False and
            intrinsic["expressionSource"] == "E09-D39-NUMBER-CONCAT", "Number intrinsic misrepresented as source formatter")
    license = document["license"]
    require(license["spdx"] == "EPL-2.0 OR GPL-3.0-or-later" and
            sha256(contained(root, license["licenseFile"])) == license["licenseFileSha256"], "Source license bytes/identity differ")
    require(b"SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later" in raw_bytes(license["readableCopyrightHeaderBytesBase64"]),
            "Original source copyright/license header missing")
    command = document["readableSourceCommand"]
    require(type(command["exitCode"]) is int and command["exitCode"] == 0 and
            command["argv"][-2:] == ["show", COMMIT + ":src/java/org/eclipse/elk/js/ElkJs.java"] and
            command["stdoutSha256"] == JAVA_SHA and command["stderrSha256"] == fingerprint(b""), "Original fixed Git command differs")
    return registry, {row["componentId"]: row for row in components}


def validate_approvals(value, document, root=ROOT):
    root = Path(root)
    require(value["schema"] == "py-elk-e09-source-approvals/v1" and
            value["sourceDocument"] == SOURCES and value["sourceDocumentSha256"] == sha256(root / SOURCES), "Source approval document binding differs")
    require(type(value["expectedComponentCount"]) is int and value["expectedComponentCount"] == len(COMPONENT_SEALS) and
            value["expectedComponentIds"] == list(COMPONENT_SEALS), "Approval whole-component denominator differs")
    require(type(value["pythonAlgorithmsVerified"]) is int and value["pythonAlgorithmsVerified"] == 0 and
            value["packagePublished"] is False, "Source approval promotes runtime/release")
    components = {row["componentId"]: row for row in document["components"]}
    reviews = {}
    for identity, record in value["reviews"].items():
        path = contained(root, record["path"])
        require(record["path"].startswith("references/e09-source-reviews/") and sha256(path) == record["sha256"], "Independent source review bytes differ")
        review = load(path)
        require(review["accepted"] is True and review["blockers"] == [], "Independent source review rejected or incomplete")
        if "sourceIdentity" in review:
            require(review["sourceIdentity"] == {"path": "lib/elk-worker.js", "sha256": WORKER_SHA,
                                                  "version": "0.12.1", "commit": COMMIT}, "Independent source review baseline differs")
        elif identity != 'V-PROVIDER-01':
            require(type(review.get("inheritsAcceptedComponents")) is dict,
                    "Independent source review baseline/inheritance missing")
        accepted = review["acceptedComponentIds"]
        require(type(accepted) is list and bool(accepted) and len(set(accepted)) == len(accepted) and
                set(accepted) <= components.keys(), "Independent source review component scope differs")
        archive = record["originalMaterialBytesBase64"]
        require(set(archive) == set(review["filesSha256"]), "Original reviewed material denominator differs")
        for original, expected in review["filesSha256"].items():
            require(fingerprint(raw_bytes(archive[original])) == expected, "Original reviewed material bytes differ")
        proposals = [_parse_json(raw_bytes(raw).decode("utf-8")) for name, raw in archive.items()
                     if ("/source-components-proposal" in name or '/source-provider-proposal' in name) and name.endswith(".json")]
        require(len(proposals) == 1, "Original reviewed source proposal missing/duplicated")
        proposal = proposals[0]
        if identity == 'V-PROVIDER-01':
            require(proposal['schema'] == 'py-elk-e09-provider-source-supplement/v1' and
                    proposal['baseline'] == {'elkjs': '0.12.1', 'commit': COMMIT, 'workerSha256': WORKER_SHA} and
                    accepted == ['E09-D40-PROVIDER-BOUNDARY'], "Provider review baseline/scope differs")
        else:
            require(proposal['baseline'] == {'version': '0.12.1', 'commit': COMMIT},
                    'Original reviewed source proposal baseline differs')
            require(any(row['sourceId'] == 'fixed-worker' and row['sha256'] == WORKER_SHA
                        for row in proposal['sources']), 'Original reviewed worker identity differs')
        for component in accepted:
            original_components = [proposal['component']] if identity == 'V-PROVIDER-01' else proposal['components']
            original_rows = [item for item in original_components if item['componentId'] == component]
            require(len(original_rows) == 1 and all(
                    components[component][field] == original_rows[0][field]
                    for field in ('sourceId', 'symbol', 'startLine', 'endLine', 'spanSha256', 'actualCaller', 'approvedScopeProposal')),
                    'Reviewed component caller/scope differs from original approved proposal')
            names = [name for name in archive if name.endswith("/" + component + ".txt")]
            require(len(names) == 1 and raw_bytes(archive[names[0]]) == raw_bytes(components[component]["sourceBytesBase64"]),
                    "Reviewed source span differs from component material")
        reviews[identity] = review
    for identity, review in reviews.items():
        if "sourceIdentity" not in review and identity != 'V-PROVIDER-01':
            inherited = review["inheritsAcceptedComponents"]
            parents = [reviews[key] for key, record in value["reviews"].items() if record["sha256"] == inherited["sha256"]]
            require(len(parents) == 1 and "sourceIdentity" in parents[0] and
                    set(list(COMPONENT_SEALS)[:12]) <= set(parents[0]["acceptedComponentIds"]),
                    "Independent source subset omits its fixed monitor base review")
    rows = value["approvals"]
    require(type(rows) is list and len({row["componentId"] for row in rows}) == len(rows), "Duplicate source component approval")
    for row in rows:
        identity = row["componentId"]
        require(identity in components and row["status"] == "approved-observation-only" and row["runtimeAccepted"] is False and
                row["spanSha256"] == components[identity]["spanSha256"], "Component source approval scope/seal differs")
        require(row["reviewId"] in reviews and identity in reviews[row["reviewId"]]["acceptedComponentIds"], "Independent review omits approved component")
    require({row["componentId"] for row in rows} == set(COMPONENT_SEALS) and value["status"] == "approved-for-ADR0008-diagnostics-only",
            "Whole diagnostics source approval remains pending")
    return len(rows)


def _symbol(root, reference, *, assertion=False):
    """Resolve the real qualified AST node without importing/dispatching code."""
    path = contained(root, reference['path'])
    require(path.suffix == '.py', 'Branch symbol is not Python source')
    node = ast.parse(path.read_text(encoding='utf-8-sig'), filename=reference['path'])
    container = None
    for part in reference['symbol'].split('.'):
        found = [child for child in node.body if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                 and child.name == part]
        require(len(found) == 1, 'Branch symbol missing/ambiguous: ' + reference['path'] + ':' + reference['symbol'])
        container, node = node, found[0]
    if assertion:
        require(reference['path'].startswith('tests/') and node.name.startswith('test_') and
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)), 'Branch assertion is not a real test method')
        def contains_assertion(current, visited):
            if current.name in visited:
                return False
            visited.add(current.name)
            for child in ast.walk(current):
                if isinstance(child, ast.Assert):
                    return True
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    function = child.func
                    if isinstance(function.value, ast.Name) and function.value.id == 'self':
                        if function.attr.startswith('assert'):
                            return True
                        if isinstance(container, ast.ClassDef):
                            helpers = [method for method in container.body if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                                       and method.name == function.attr]
                            if len(helpers) == 1 and contains_assertion(helpers[0], visited):
                                return True
            return False
        require(contains_assertion(node, set()), 'Branch test has no assertion: ' + reference['symbol'])
    return node


def validate_branch_matrix(document, root=ROOT):
    """Validate finite declaration semantics, never read future runtime receipts.

    Runtime validator must separately recompute geometry/API/newcoverage receipts
    and compare their full installed identity and candidate interpreter. A valid
    matrix alone cannot authenticate any execution or prove branch traversal.
    """
    root = Path(root)
    try:
        require(document['schema'] == 'py-elk-e09-branch-matrix/v1' and
                document['scope'] == 'E09-ADR0008-revision1' and
                document['status'] == 'declarations-frozen-runtime-acceptance-separate', 'Branch matrix identity/status differs')
        require(document['wholeAlgorithmAccepted'] is False and document['packagePublished'] is False and
                document['runtimeAccepted'] is False, 'Branch declarations promote runtime/release acceptance')
        expected_count = len(REQUIRED_DECLARATIONS)
        branch_count = sum(row[0] for row in REQUIRED_DECLARATIONS.values())
        require(type(document['requiredDeclarationCount']) is int and document['requiredDeclarationCount'] == expected_count and
                type(document['declaredBranchCount']) is int and document['declaredBranchCount'] == branch_count,
                'Branch declaration/count denominator differs')
        rows = document['rows']
        require(type(rows) is list and len(rows) == expected_count and
                [row['id'] for row in rows] == list(REQUIRED_DECLARATIONS), 'Required branch IDs/order differ')
        for row in rows:
            count, role, seal = REQUIRED_DECLARATIONS[row['id']]
            require(fingerprint(canonical(row).encode('utf-8')) == seal and len(row['branches']) == count and
                    row['evidenceRole'] == role, 'Required branch declaration differs: ' + row['id'])
            require(set(row['sourceComponents']) <= COMPONENT_SEALS.keys(), 'Branch refers to unapproved source component')
            for reference in row['implementation']:
                _symbol(root, reference)
            for reference in row['assertions']:
                _symbol(root, reference, assertion=True)
        require(canonical(document['profile']) == canonical(REQUIRED_PROFILE), 'First-release declared profile differs')
        profiles = load(root / 'docs/release-profiles.json')['profiles']
        selected = [profile for profile in profiles if profile['id'] == 'basic-layered']
        require(len(selected) == 1, 'First-release profile missing/duplicated')
        profile = selected[0]
        require(canonical(profile['inputDomain']) == canonical(REQUIRED_PROFILE['inputDomain']) and
                profile['algorithms'] == [REQUIRED_PROFILE['algorithm']] and
                set(profile['options']) == set(REQUIRED_PROFILE['optionIds']) and len(profile['options']) == 9 and
                profile['edgeRouting'] == ['ORTHOGONAL'] and profile['nestedGraphs'] is False and
                profile['ports'] is False and profile['independentLabelLayout'] is False and
                profile['mermaidIntegrationRequired'] is False, 'Current release-profile scope/bounds differ')
        host = load(root / 'references/e09-host-contract.json')
        require(host['id'] == 'E09-ADR0008-revision1' and host['loggingTrueSupported'] is True and
                host['measureExecutionTimeTrueSupported'] is True and host['registration']['optionCount'] == 9 and
                host['referenceDenominators'] == {'algorithms': 12, 'options': 243, 'categories': 8, 'masterCases': 25},
                'Current E09 host diagnostic/denominator contract differs')
        metadata = load(root / 'references/e09-metadata-schema.json')['expectedQueries']
        default = metadata['default']
        require({name: len(default[name]) for name in ('algorithms', 'options', 'categories')} ==
                REQUIRED_PROFILE['nativeRegistryCounts'], 'Current metadata registration denominator differs')
        require(default['algorithms'][0]['id'] == REQUIRED_PROFILE['algorithm'] and
                {row['id'] for row in default['options']} == set(REQUIRED_PROFILE['optionIds']),
                'Current metadata algorithm/option IDs differ')
        constraints = default['algorithms'][0]['native']['constraints']
        domain = REQUIRED_PROFILE['inputDomain']
        require(canonical(constraints['originalChildNodes']) == canonical(domain['originalChildNodes']) and
                canonical(constraints['originalEdges']) == canonical(domain['originalEdges']) and
                constraints['directions'] == domain['directions'] and constraints['flatRootChildrenOnly'] is True,
                'Current metadata layout constraints differ')
        # Reuse the source-independent catalogue contract for exact source
        # fields/order, eight applicable options, native accepted/default values,
        # unsupported capabilities, empty registry and E09 diagnostics flags.
        from validate_e08_api import native_metadata_contract
        native_metadata_contract(root)
        lock = load(root / 'UPSTREAM.json')
        require(lock['metadataCapture']['counts'] == REQUIRED_PROFILE['fullReferenceCounts'] and
                lock['python']['implementedAlgorithms'] == [], 'Full catalogue/algorithm denominator was reduced/promoted')
        require(canonical(document['plannedEvidence']) == canonical(PLANNED_EVIDENCE),
                'Planned same-wheel evidence paths/roles differ')
        for role, evidence in PLANNED_EVIDENCE.items():
            # Resolve the pure validator only; a planned receipt need not exist yet.
            module, function = evidence['validator'].split('.')
            _symbol(root, {'path': 'scripts/' + module + '.py', 'symbol': function})
        suite = load(root / 'references/layout/suite.json')['cases']
        require(type(document['masterCaseCount']) is int and document['masterCaseCount'] == 25 and
                len(suite) == 25 and len(document['masterCases']) == 25 and
                [row['id'] for row in document['masterCases']] == list(MASTER_CASES) == [row['id'] for row in suite],
                'Full25 master denominator/order differs')
        for row, case in zip(document['masterCases'], suite):
            status, fingerprint_value = MASTER_CASES[row['id']]
            require(row['classification'] == status and row['requestSha256'] == fingerprint_value and
                    row['request'] == 'tests/fixtures/validation/' + case['request'] and
                    sha256(contained(root, row['request'])) == fingerprint_value and row['evidenceRole'] == 'newcoverage' and
                    type(row['reason']) is str and bool(row['reason']) and
                    status == ('supported' if case['expectedOutcome'] == 'returned' else 'expected-error'),
                    'Master request/classification differs: ' + row['id'])
        return {'schema': 'py-elk-e09-branch-matrix-validation/v1', 'passed': True, 'errors': [],
                'requiredDeclarationCount': expected_count, 'declaredBranchCount': branch_count, 'masterCaseCount': 25,
                'plannedEvidenceRoles': list(PLANNED_EVIDENCE), 'runtimeAcceptanceAssessed': False,
                'runtimeReceiptsRead': False, 'packagePublished': False}
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, SyntaxError) as error:
        return {'schema': 'py-elk-e09-branch-matrix-validation/v1', 'passed': False, 'errors': [str(error)],
                'requiredDeclarationCount': len(REQUIRED_DECLARATIONS),
                'declaredBranchCount': sum(row[0] for row in REQUIRED_DECLARATIONS.values()),
                'runtimeAcceptanceAssessed': False, 'runtimeReceiptsRead': False}


def check(root=ROOT, *, with_upstream=False):
    root = Path(root); errors = []; approved = 0; facts = False
    try:
        document = load(root / SOURCES)
        registry, components = validate_source_facts(document, root); facts = True
        approval = load(root / APPROVALS)
        approved = len(approval["approvals"])
        approved = validate_approvals(approval, document, root)
        if with_upstream:
            import upstream
            for identity, row in registry.items():
                if identity == "readable-ElkJs":
                    raw = upstream.git(root / ".local/upstream-elkjs", "show", COMMIT + ":" + row["path"])
                else:
                    raw = (root / ".local/npm-elkjs/package" / row["path"]).read_bytes()
                require(fingerprint(raw) == row["sha256"], "Actual fixed source bytes differ")
                lines = raw.decode("utf-8").splitlines()
                for component in components.values():
                    if component["sourceId"] == identity:
                        span = ("\n".join(lines[component["startLine"] - 1:component["endLine"]]) + "\n").encode()
                        require(span == raw_bytes(component["sourceBytesBase64"]), "Actual fixed source range differs")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e09-source-validation/v1", "status": "FAIL" if errors else "E09_DIAGNOSTICS_SOURCE_SCOPE_APPROVED",
            "passed": not errors, "errors": errors, "approvedComponentCount": approved,
            "expectedComponentCount": len(COMPONENT_SEALS), "sourceFactsVerified": facts,
            "canonicalVerified": bool(with_upstream and not errors), "runtimeAcceptanceAssessed": False,
            "pythonAlgorithmsVerified": 0, "packagePublished": False,
            "limitation": "Fixed source/review material and limited observational approval only; runtime, exact numeric formatter behavior and same-wheel coverage are separate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true")
    parser.add_argument("--branch-matrix", action="store_true", help="Also validate static first-release branch declarations; no runtime receipts read")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(); result = check(with_upstream=args.with_upstream)
    if args.branch_matrix:
        try:
            matrix = validate_branch_matrix(load(ROOT / BRANCH_MATRIX))
        except (ValueError, OSError, KeyError, TypeError) as error:
            matrix = {'passed': False, 'errors': [str(error)]}
        result['branchMatrixValidation'] = matrix
        if matrix['passed'] is not True:
            result['passed'] = False
            result['status'] = 'FAIL'
            result['errors'].extend(matrix['errors'])
    if args.out:
        write(args.out, result)
    print(json.dumps(result, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
