"""Pure saved-evidence acceptance for explicit TASKS M6 / E13--E15 conditions.

No layout, oracle, test suite, installation or performance process is invoked.
Existing options/branches archives are reused; advanced.zip contains only the
additional ignored evidence actually needed here. All paths fail closed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
JSON = Path('docs/iterations/E13_E15_ACCEPTANCE.json')
MD = Path('docs/iterations/E13_E15_ACCEPTANCE.md')
ARCHIVE = Path('references/full-native-closure/advanced.zip')
MANIFEST = Path('references/full-native-closure/advanced.manifest.json')
OLD_ROOT = 'C:/code/py-visactor/py-elk'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if value is not True:
        raise ValueError(message)


def name(path):
    value = str(path).replace('\\', '/')
    if value.startswith(OLD_ROOT + '/'):
        value = value[len(OLD_ROOT) + 1:]
    p = Path(value)
    if p.is_absolute() or ':' in value or '..' in p.parts:
        raise ValueError('Escaping evidence path: ' + value)
    return value


def ignored(path):
    return path.startswith(('test-runs/', '.local/'))


def exact(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(exact(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    return a == b


class Evidence:
    def __init__(self, *, sealing=False):
        self.sealing = sealing
        self.files = {}
        self.archives = []
        self.managed = None
        self.direct = None
        if sealing:
            process = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'],
                                     capture_output=True, check=True)
            self.direct = {value.decode('utf-8') for value in process.stdout.split(b'\0') if value}
        for kind in ('options', 'branches', 'algorithms', 'advanced'):
            mp = f'references/full-native-closure/{kind}.manifest.json'
            if not (ROOT / mp).is_file():
                if kind == 'advanced' and sealing:
                    continue
                raise ValueError('Missing explicit archive manifest: ' + mp)
            mraw = (ROOT / mp).read_bytes()
            manifest = json.loads(mraw)
            if kind == 'options':
                ap, expected = manifest['archive']['path'], manifest['archive']['sha256']
                members = {x['path']: x['sha256'] for x in manifest['files'] if x['storage'] == 'archive'}
            elif kind == 'branches':
                ap, expected = manifest['archive'], manifest['archiveSha256']
                members = manifest['members']
            elif kind == 'algorithms':
                require(manifest['schema'] == 'pyelk-algorithm-acceptance-evidence/v1', 'Unknown algorithm archive schema')
                ap, expected = manifest['archive']['path'], manifest['archive']['sha256']
                members = {x['path']: x['sha256'] for x in manifest['members']}
            else:
                require(manifest['schema'] == 'pyelk-advanced-acceptance-evidence/v1', 'Unknown advanced schema')
                ap, expected = manifest['archive']['path'], manifest['archive']['sha256']
                members = {x['path']: x['sha256'] for x in manifest['members']}
                require(len(members) == len(manifest['members']), 'Duplicate advanced archive member')
                require(all(name(x) == x for x in members), 'Invalid advanced member path')
                self.managed = manifest
                if not sealing:
                    self.direct = {x['path'] for x in manifest['repositoryDependencies']}
                    require(self.direct.isdisjoint(members), 'Mixed tracked/archive evidence classification')
            require(name(ap) == f'references/full-native-closure/{kind}.zip', 'Archive location differs')
            zraw = (ROOT / ap).read_bytes()
            require(sha(zraw) == expected, 'Archive SHA differs: ' + ap)
            z = zipfile.ZipFile(io.BytesIO(zraw))
            require(len(z.namelist()) == len(members) and set(z.namelist()) == members.keys(),
                    'Archive membership differs: ' + ap)
            self.archives.append((ap, z, members))
            # Reused archives remain ordinary tracked dependencies.
            if kind != 'advanced':
                self.files[mp] = dict(path=mp, sha256=sha(mraw), bytes=len(mraw), storage='repository')
                self.files[ap] = dict(path=ap, sha256=sha(zraw), bytes=len(zraw), storage='repository')
            else:
                self.managed_storage = {'archive': dict(path=ap, sha256=sha(zraw), bytes=len(zraw)),
                                        'manifest': dict(path=mp, sha256=sha(mraw))}

    def raw(self, path, expected=None):
        path = name(path)
        storage = 'repository'
        if path in self.direct:
            raw = (ROOT / path).read_bytes()
        else:
            choices = [(ap, z, members[path]) for ap, z, members in self.archives
                       if path in members and (expected is None or members[path] == expected)]
            if choices:
                require(len({value for _, _, value in choices}) == 1, 'Ambiguous raw evidence revision: ' + path)
                ap, z, member_sha = choices[0]
                raw = z.read(path)
                require(sha(raw) == member_sha, 'Archive member SHA differs: ' + path)
                storage = ap
            elif self.sealing:
                raw = (ROOT / path).read_bytes()
                storage = 'unsealed-untracked'
            else:
                raise ValueError('Non-repository evidence has no explicit archive member: ' + path)
        require(expected is None or sha(raw) == expected, 'Evidence SHA differs: ' + path)
        row = dict(path=path, sha256=sha(raw), bytes=len(raw), storage=storage)
        if path in self.files:
            require(self.files[path] == row, 'Mixed evidence revisions: ' + path)
        self.files[path] = row
        return raw

    def json(self, path, expected=None):
        return json.loads(self.raw(path, expected))

    def binding(self, path, expected=None):
        self.raw(path, expected)
        return self.files[name(path)]

    def binding_objects(self, value):
        work = [value]
        while work:
            current = work.pop()
            if isinstance(current, dict):
                if isinstance(current.get('path'), str) and isinstance(current.get('sha256'), str):
                    self.binding(current['path'], current['sha256'])
                work.extend(current.values())
            elif isinstance(current, list):
                work.extend(current)

    def closure(self):
        if not self.sealing:
            used = {p: v for p, v in self.files.items() if v['storage'] == ARCHIVE.as_posix()}
            declared = {x['path']: x for x in self.managed['members']}
            require(used == declared, 'Advanced archive is not the exact additional raw closure')
            actual_direct = {p: v for p, v in self.files.items() if v['storage'] == 'repository'}
            declared_direct = {x['path']: x for x in self.managed['repositoryDependencies']}
            require(actual_direct == declared_direct, 'Direct repository dependency closure differs')


def observe_result(value):
    if 'result' in value:
        return value['result']
    if 'actual' in value:
        return value['actual']
    raise ValueError('Unknown saved geometry observation shape')


def make(*, sealing=False):
    e = Evidence(sealing=sealing)
    authority = {p: e.binding(p) for p in ('docs/TASKS.md', 'docs/ITERATION_PLAN.md')}
    e.binding('scripts/advanced_geometry.py')
    e.binding('tests/validation/test_advanced_geometry.py')
    spec = importlib.util.spec_from_file_location('advanced_saved_acceptance', ROOT / 'scripts/advanced_geometry.py')
    geometry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geometry)
    summary_path = 'test-runs/20261104-HOST-19/A/full-layered-summary-01.json'
    summary = e.json(summary_path)
    calls = []
    for case in summary['cases']:
        cid = case['id']
        folder = f'test-runs/20261104-HOST-19/A/{case["batch"]}/{cid}'
        request = e.binding(f'tests/fixtures/suites/full-native-layered/requests/{cid}.json', case['requestSha256'])
        reference = e.json(folder + '/reference.json', case['referenceSha256'])
        native = e.json(folder + '/candidate.json', case['candidateSha256'])
        comparison = e.json(folder + '/comparison.json', case['comparisonSha256'])
        require(reference['requestSha256'] == native['requestSha256'] == request['sha256'], 'Public request binding differs')
        if case['matched']:
            require(reference['outcome'] == native['outcome'] == 'returned'
                    and comparison['comparison']['differences'] == [] and comparison['passed'] is True,
                    'Saved successful public comparison differs')
        calls.append({'id': cid, 'matched': case['matched'], 'request': request,
                      'reference': e.files[folder + '/reference.json'], 'native': e.files[folder + '/candidate.json'],
                      'comparison': e.files[folder + '/comparison.json'],
                      'sourceOutcome': reference['outcome'], 'nativeOutcome': native['outcome'],
                      'sourceError': reference.get('error'), 'nativeError': native.get('error')})
    require(len(calls) == 72 and sum(x['matched'] for x in calls) == 66, 'Saved public denominator differs')

    old_path = 'test-runs/full-native-closure/A/advanced-geometry-final/report.json'
    old = e.json(old_path)
    historical_counts = Counter()
    current_counts = Counter()
    current_statuses = Counter()
    checked_rows = []
    for row in old['rows']:
        req = e.json(row['request']['path'], row['request']['sha256'])
        observation = e.json(row['observation']['path'], row['observation']['sha256'])
        recorded = e.json(row['report']['path'], row['report']['sha256'])
        require(recorded['errors'] == [] and recorded['assessedPredicatesPassed'] is True,
                'Historical applicable geometric predicate failed')
        current = geometry.validate(req, observe_result(observation))
        require(current['errors'] == [], 'Current saved-geometry predicate failed: ' + row['id'])
        original = Counter((x['path'], x['predicate']) for x in recorded['checked'])
        available = Counter((x['path'], x['predicate']) for x in current['checked'])
        require(all(available[k] >= v for k, v in original.items()), 'An old geometric predicate lost its premise')
        historical_counts.update(x['predicate'] for x in recorded['checked'])
        current_counts.update(x['predicate'] for x in current['checked'])
        current_statuses[current['status']] += 1
        checked_rows.append({'id': row['id'], 'role': row['role'], 'request': e.files[name(row['request']['path'])],
                             'observation': e.files[name(row['observation']['path'])],
                             'historicalReport': e.files[name(row['report']['path'])],
                             'historicalStatus': recorded['status'], 'currentSavedStatus': current['status'],
                             'historicalPredicateCount': len(recorded['checked']),
                             'currentSavedPredicateCount': len(current['checked']),
                             'currentNotAssessed': current['not_assessed'], 'currentErrors': current['errors']})
    require(len(checked_rows) == 142, 'Historical independent geometry denominator differs')

    delta_path = 'docs/changes/20261104-advanced-geometry-contracts.json'
    delta = e.json(delta_path)
    for path, expected in delta['filesSha256'].items():
        e.binding(path, expected)
    fixture_folder = 'tests/fixtures/suites/full-option-effects/geometry-contracts'
    fixture_manifest = e.json(fixture_folder + '/manifest.json')
    fixtures = {}
    for case in fixture_manifest['cases']:
        files = {}
        for filename, binding in case['files'].items():
            path = f'{fixture_folder}/{case["id"]}/{filename}'
            files[filename] = e.json(path, binding['sha256'])
        fixtures[case['id']] = files
    sensitive = []
    for row in delta['rows']:
        binding = row['bindings']
        if 'request' in binding:
            req = e.json(binding['request'].get('member') or binding['request']['path'], binding['request']['sha256'])
            observation = e.json(binding['observation'].get('member') or binding['observation']['path'], binding['observation']['sha256'])
        else:
            req = fixtures[row['id']]['request.json']
            observation = fixtures[row['id']]['reference.json' if row['role'] == 'reference' else 'candidate.json']
        result = geometry.validate(req, observe_result(observation))
        require(result['errors'] == [], 'Sensitive geometric predicate failed')
        present = Counter((x['path'], x['predicate']) for x in result['checked'])
        needed = Counter((x['path'], x['predicate']) for x in row['newOrNewlySensitivePredicates'])
        require(all(present[k] >= v for k, v in needed.items()), 'Sensitive geometric premise disappeared')
        sensitive.append({'id': row['id'], 'role': row['role'], 'status': result['status'],
                          'newOrSensitivePredicates': row['newOrNewlySensitivePredicates'], 'errors': result['errors']})
    cell = fixtures['label-cell-stacks']
    stacks = []
    for item in cell['request.json']['cases']:
        if item['cell']['kind'] != 'label':
            continue
        axis = 1 if item['cell']['horizontalMode'] else 0
        for role, values, value_key in (('reference', cell['reference.json']['results'], 'value'),
                                         ('candidate', cell['candidate.json']['rows'], 'actual')):
            rectangles = next(x[value_key]['labels'] for x in values if x['id'] == item['id'])
            result = geometry.validate_label_stack(rectangles, axis, item['cell']['gap'])
            require(result['errors'] == [] and result['status'] == 'PASS', 'Prepared LabelCell gap failed')
            stacks.append({'id': item['id'], 'role': role, 'axis': axis, 'gap': item['cell']['gap'], 'report': result})
    require(len(sensitive) == 24 and len(stacks) == 4, 'Advanced geometry delta denominator differs')
    handoff_path = 'test-runs/full-native-closure/A/advanced-contracts-01/handoff.json'
    handoff = e.json(handoff_path)
    for entry in handoff['validation']:
        command = e.json(entry['command'])
        require(command['exitCode'] == 0, 'Recorded checker test command failed')

    core = {}
    for key, path in (
        ('recursive', 'test-runs/20261104-FULL/V/public-core-01/report.json'),
        ('coordinateModes', 'test-runs/20261104-FULL/V/json-transfer-public-01/report.json'),
    ):
        report = e.json(path)
        require(report['passedCount'] == report['caseCount'], 'Core public path failed')
        core[key] = {'report': e.files[path], 'caseCount': report['caseCount'], 'cases': report['cases'],
                     'scope': report['coverage'], 'notCovered': report['notCovered']}

    matrix_path = 'docs/iterations/FULL_DECLARED_BRANCH_MATRIX.json'
    matrix = e.json(matrix_path)
    e.binding_objects(matrix)
    require(len(matrix['rows']) == 90 and len(matrix['supplementalRows']) == 121, 'Finite branch denominator differs')
    remaining = [x['id'] for x in matrix['supplementalRows'] if x['status'] == 'no_variant_witness']
    # The branch writer owns its specialized assertion and routing checks. This
    # acceptance map binds its entire raw witness closure, without converting
    # helper/state/alias/boundary statuses into geometric equivalence.
    core_statuses = {'witnessed_scoped', 'shared_body_alias_verified', 'source_raw_unconstructible_boundary',
                     'causal_consumer_chain_scoped'}
    for row in matrix['rows']:
        require(row['status'] in core_statuses, 'Unaccounted core factory or unknown core scope')
    supplemental_statuses = {'witnessed_scoped', 'configuration_state_scoped', 'source_route_state_scoped',
                             'scheduler_exclusion_scoped', 'identity_order_boundary_scoped', 'no_variant_witness'}
    require(all(row['status'] in supplemental_statuses for row in matrix['supplementalRows']),
            'Unknown supplemental acceptance scope')
    require(matrix['summary']['supplementalStatuses'] == dict(Counter(row['status'] for row in matrix['supplementalRows']))
            and matrix['summary']['coreStatuses'] == dict(Counter(row['status'] for row in matrix['rows'])),
            'Finite branch status counts differ from actual rows')
    require(all(row['witnesses'] and row['sourceEvidence'] and row['limitations']
                for row in matrix['supplementalRows'] if row['status'] != 'no_variant_witness'),
            'A scoped supplemental row lacks its witnesses, Source anchors or limitations')
    core_accounted = (matrix['summary']['coreRowsAccountedForWithinStatedScope'] is True
                      and matrix['summary']['unwitnessedCoreIds'] == [])
    enums_accounted = not remaining and all(row['status'] in supplemental_statuses - {'no_variant_witness'}
                                          for row in matrix['supplementalRows'])
    if enums_accounted:
        require(matrix['summary'].get('allDeclaredEnumRowsAccountedForWithinStatedScope') is True
                and matrix['summary']['unwitnessedEnumIds'] == [], 'Finite branch accounting summary differs')
    strong_enums_accepted = (matrix['summary']['allDeclaredEnumBranchesAccepted'] is True
                            and all(row['status'] == 'witnessed_scoped' for row in matrix['supplementalRows']))
    require(matrix['summary']['allDeclaredEnumBranchesAccepted'] is not True or strong_enums_accepted,
            'Scoped configuration/exclusion/boundary promoted to unconditional direct branch acceptance')
    option_roles = e.json('docs/iterations/FULL_OPTION_ROLES.json')
    for row in option_roles['rows']:
        e.binding_objects(row.get('additionalRoleWitnesses', []))
    e.binding('docs/option-coverage.json')
    published_path = 'docs/releases/evidence/published-0.1.0/wheel-installed.json'
    published = e.json(published_path)
    require(len(published['runtimeFilesSha256']) == 208, 'Published runtime denominator differs')
    for path, expected in published['runtimeFilesSha256'].items():
        e.binding('src/' + path, expected)
    require(published['installedObservation']['metadata'] == [12, 243, 8], 'Installed metadata denominator differs')
    e.binding('docs/decisions/0010-native-object-identity.md')
    e.binding('docs/decisions/0014-saved-hierarchy-shape-hashes.md')
    e.binding('docs/ADVANCED_GEOMETRY.md')

    def condition(cid, iteration, text, evidence, finding, limitations=(), status='met_scoped'):
        return dict(id=cid, iteration=iteration, explicitCondition=text, status=status,
                    evidence=evidence, finding=finding, limitations=list(limitations))

    requirements = [
        condition('M6-01-ports', 'E13', 'side/index/order/position/ratio; independent constraints and anchors',
                  ['public72', 'historical142', 'geometryDelta24'],
                  'Actual FIXED_SIDE/ORDER/POS/RATIO public cases and explicit/default anchors are complemented by independent side/anchor, clockwise order, rectangle-origin tangent and owner-resize ratio predicates.',
                  ['Order premise: unique indices, equal sizes/anchors, roomy BEGIN alignment. No tie/overfull Cartesian guarantee.']),
        condition('M6-01-size', 'E13', 'Node dimensions and applicable port/label size constraints',
                  ['public72', 'historical142', 'geometryDelta24'],
                  'Given-size preservation, nested containment and positive explicit minimum bounds are checked on actual input/output rectangles.',
                  ['Explicit ordinary leaf MINIMUM_SIZE scope; no claim every inherited/default size combination was executed.']),
        condition('M6-02-label-position-size', 'E13', 'Node/port/edge given-size labels, positioning and spacing',
                  ['public72', 'historical142', 'geometryDelta24', 'preparedLabelCell4'],
                  'Actual CENTER/HEAD/TAIL, node and port labels have full-result differentials; independent given dimensions/INSIDE containment and actual selected LabelCell axis/gap3 or2 checks supply separate geometry.',
                  ['Actual prepared LabelCell states are not extra public calls. OUTSIDE alone is not a promise of universal collision freedom.']),
        condition('M6-02-missing-size', 'E13', 'Missing label dimensions policy',
                  ['geometryContractFixtures', 'geometryDelta24'],
                  'New real public Layered input omits width/height on2node+2port+1edge labels. Both engines return0x0 and preserve text/id; independent missing-dimension predicates and mutation controls exist.',
                  ['No label manager/font measurement; node/port dimensions explicitly supplied.']),
        condition('M6-03-compound', 'E14', 'Real recursive/compound/cluster/cross-hierarchy layout',
                  ['public72', 'corePublic', 'historical142'],
                  'Nested include-children graphs, labelled cross-hierarchy edges, DOWN transforms and valid nested external ports have genuine full calls. Independent containment and global-frame endpoint attachment test real nested offsets.',
                  ['Cluster means the actual JSON compound/container model. It is not a claim of a separate clustering algorithm or arbitrary nesting combinations.']),
        condition('M6-03-frames', 'E14', 'JSON coordinate modes, container backfill and endpoint transforms',
                  ['corePublic', 'historical142'],
                  'Four real Source/native coordinate-mode observations plus independent fixed-input export-frame, common-ancestor container and nested global endpoint predicates exist.',
                  ['Four frame modes and compound cases are separately witnessed; no full mode x every-label x every-routing product is asserted.']),
        condition('M6-03-sections', 'E14', 'Section connectivity validation',
                  ['geometryContractFixtures', 'geometryDelta24'],
                  'A real public Fixed/POLYLINE2section chain retains s0.end=s1.start, reciprocal section references and n0/n1 shape endpoints. Independent continuity/reciprocity checks reject separately corrupted facts.',
                  ['Given geometry through actual importer/exporter/layout, not a synthetic positive. No arbitrary section graph or all compound-merge=false guarantee.']),
        condition('M6-04-main', 'E15', 'Complete cycle/layer/crossing/placement/default/numeric/PRNG strategy matrix',
                  ['finiteBranches90', 'public72', 'sourceIndex'],
                  'Core9P1/9P2/4P3/5P4/4routing+59intermediate factories are classified through actual task/body/state, aliases, causal consumer or justified Source boundaries.',
                  ['Core accounting is not121 supplemental enum branches or every internal graph predicate. Historical executions retain original source/version scopes.'],
                  status='met_core_scoped'),
        condition('M6-04-M6-05-declared-branches', 'E15', 'Per-declared-branch Source/differential/geometry acceptance and applicable Layered options',
                  ['finiteBranches90', 'optionRoleMap', 'frozenOptionLedger'],
                  ('All121 supplemental rows are accounted at their actual scoped witness strength, including configuration/route state, scheduler exclusion and the retained identity-order boundary. Static/default/parser/input mentions are not runtime effects.'
                   if enums_accounted else 'The finite121-row supplemental map still contains explicitly unverified values, listed below. Static/default/parser/input mentions do not satisfy runtime consumption.'),
                  ['Numeric values and graph combinations are not an infinite test denominator. Role/state/diagnostic/metadata/unconstructible options must be classified at their actual role.'],
                  status='met_scoped' if enums_accounted and core_accounted else 'pending_finite_variant_witnesses'),
        condition('M6-05-routing', 'E15', 'Polyline/spline/complex edges and sections',
                  ['public72', 'historical142', 'geometryDelta24', 'finiteBranches90'],
                  'Real orthogonal/polyline/spline and long/feedback/self-loop paths have separate differentials. Independent orthogonality, endpoint attachment and nonempty CONSERVATIVE3k+1 control-net predicates are observed.',
                  ['No universal spline obstacle avoidance or optimality. SLOPPY/preserved/compound paths do not all promise the conservative cubic representation.']),
        condition('M6-05-components', 'E15', 'Complete component packing and applicable constraints',
                  ['public72', 'finiteBranches90', 'historical142'],
                  'Actual component strategies and compaction callers are present, including nested/external-side components. Independent container/endpoint predicates and component-level object states accompany public results.',
                  ['ADR0010 native process identity policy does not reproduce all GWT allocation histories; the retained23 prepared internal ordering differences are not exact-order PASS.', 'No global packing optimum required.']),
        condition('M6-05-edge-domain', 'E15', 'Primitive/hyperedge applicability is explicit',
                  ['sourceIndex', 'public72', 'finiteBranches90'],
                  'Primitive/extended import and shared-port hyperedge processing are distinguished from unsupported multi-source/multi-target raw Layered edges.',
                  ['The compiled Source itself rejects raw multi-source/multi-target edges; declaring that boundary is not inventing missing successful hyperedge geometry.']),
    ]
    e15_met = core_accounted and enums_accounted and all(row['status'] in ('met_scoped', 'met_core_scoped')
                                                       for row in requirements if row['iteration'] == 'E15')
    e.closure()
    return {'schema': 'pyelk-e13-e15-acceptance/v1', 'authority': authority,
            'scope': 'Only explicit TASKS M6-01..05 and ITERATION_PLAN E13..15 finite exit conditions.',
            'iterations': [{'id': 'E13', 'status': 'met_scoped'}, {'id': 'E14', 'status': 'met_scoped'},
                           {'id': 'E15', 'status': 'met_scoped' if e15_met else 'in_progress_finite_variants'}],
            'requirements': requirements,
            'finiteRemainingWork': {'denominator': len(matrix['supplementalRows']),
                                    'statusCounts': dict(Counter(x['status'] for x in matrix['supplementalRows'])),
                                    'unwitnessedCount': len(remaining), 'unwitnessedIds': remaining,
                                    'nextAction': ('No declared supplemental value remains unmapped. Preserve the scoped distinctions and all Source/error/identity boundaries; no additional layout or infinite-combination proof is implied.'
                                                   if e15_met else 'Map still-missing consumer families at their actual role; no old matrix rerun or infinite combinations.')},
            'public72': {'summary': e.files[summary_path], 'normalMatched': 66, 'sourceErrors': 6,
                         'calls': calls, 'sourceErrorsAreGeometryPass': False},
            'historical142': {'report': e.files[old_path], 'historicalStatuses': old['statuses'],
                              'historicalApplicablePredicates': dict(historical_counts),
                              'historicalNotAssessed': old['notAssessedPredicates'],
                              'oldReportReboundToCurrentChecker': False,
                              'currentPureSavedReevaluation': {'observations': len(checked_rows),
                                                              'statusCounts': dict(current_statuses),
                                                              'predicates': dict(current_counts)}, 'rows': checked_rows},
            'geometryDelta24': {'report': e.files[delta_path], 'handoff': e.files[handoff_path],
                               'actualJSONObservations': 24, 'actualPreparedLabelCellObservations': 4,
                               'recordedNewSensitiveChecks': delta['checkedNewOrNewlySensitivePredicates'],
                               'recordedPartialObservations': delta['partialObservationCount'],
                               'rows': sensitive, 'stacks': stacks,
                               'testExecutionScope': handoff['validation'], 'newTestExecutionsByThisTool': 0},
            'corePublic': core,
            'finiteBranches90': {'binding': e.files[matrix_path], 'denominator': matrix['denominator'],
                                 'summary': matrix['summary'],
                                 'scopesNotPromoted': ['helper/state is not whole geometry', 'manager raw Source boundaries are not successful callback mathematics', 'shared aliases are not duplicate mathematics']},
            'optionRoleMap': {'binding': e.files['docs/iterations/FULL_OPTION_ROLES.json'],
                              'scope': option_roles['schema'], 'full243EffectsClaimed': False},
            'publishedRuntime': {'receipt': e.files[published_path], 'runtime208CurrentByteExact': True,
                                 'wheelSha256': published['wheelSha256'],
                                 'oldFullMatrixExecutionsRelabelledAsPublishedReruns': False},
            'retainedBoundaries': ['Six Source failures stay error observations, not normal geometry PASS.',
                                   'Root external ports without parent: Source TypeError vs native ValueError is preserved; no exact error-name/message parity claim for that excluded Source-failure context.',
                                   'Native preserves caller input; Source mutation and generated hashes are separately retained under explicit existing rules.',
                                   'No universal OUTSIDE collision freedom, spline avoidance, optimal packing or infinite option cross-products are required by this closure.'],
            'previousScopedBaseline': {
                'documentSha256': '01a2442c477f683ce143ea9b20356e63949ba088fb6fc57eed4325cbabd90e3b',
                'evidenceBindings': 931,
                'storageCounts': {'repository': 366, 'advanced': 177, 'options': 50, 'branches': 338},
                'retainedScopes': ['72 public cases:66 normal matches and6 Source-error observations',
                                   '142 historical independent geometry:102PASS/40PARTIAL/188 not-assessed',
                                   '24 sensitive JSON observations plus4 prepared LabelCell states',
                                   '23 prepared identity-order differences remain raw false',
                                   'Historical runtime versions are not relabelled as new published-package runs'],
                'incrementScope': 'Final finite branch mapping and five saved-only role witnesses. Previous execution scopes and negative observations are retained; no product reruns.'},
            'newExecutions': dict(products=0, source=0, tests=0, installs=0),
            'allE15RequirementsMetWithinDeclaredScope': e15_met,
            'allE15BranchesAccepted': strong_enums_accepted,
            'e20E21Complete': False,
            'evidenceStorage': getattr(e, 'managed_storage', None),
            'pathPolicy': {'explicitRootMap': {OLD_ROOT: '.'}, 'unlistedIgnoredEvidence': 'fail',
                           'implicitWorkspaceFallback': False},
            'evidence': sorted(e.files.values(), key=lambda x: x['path'])}


def seal():
    d = make(sealing=True)
    e = Evidence(sealing=True)
    members = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for entry in d['evidence']:
            if entry['storage'] not in ('unsealed-untracked', ARCHIVE.as_posix()):
                continue
            raw = e.raw(entry['path'], entry['sha256'])
            item = dict(entry, storage=ARCHIVE.as_posix())
            members.append(item)
            info = zipfile.ZipInfo(entry['path'], (2026, 11, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, raw, compresslevel=9)
    raw = buffer.getvalue()
    manifest = {'schema': 'pyelk-advanced-acceptance-evidence/v1',
                'archive': dict(path=ARCHIVE.as_posix(), sha256=sha(raw), bytes=len(raw)),
                'members': members, 'explicitRootMap': {OLD_ROOT: '.'},
                'repositoryDependencies': [x for x in d['evidence'] if x['storage'] == 'repository'],
                'classification': 'Actual source-repository git ls-files index membership at seal; not inferred from directory prefixes or temporary force-add.',
                'scope': 'Only additional non-index raw actually read; reuse options/branches/algorithms archives without copying them or source snapshots.',
                'productsExecuted': 0, 'sourceExecuted': 0}
    (ROOT / ARCHIVE).write_bytes(raw)
    (ROOT / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')


def markdown(data):
    lines = ['# E13–E15 acceptance against explicit finite conditions', '',
             ('E13/E14/E15 meet the explicit finite conditions within their recorded scopes. All declared enum rows are accounted; configuration, route-state, scheduler-exclusion and identity-order boundaries are not promoted to full raw or geometry parity.'
              if data['allE15RequirementsMetWithinDeclaredScope'] else 'E13/E14 meet the stated capabilities within recorded applicable scopes. E15 remains in progress for its finite supplemental variant witnesses.')
             + ' No Source/layout/test run is executed by this map. E20/E21 completion is not asserted.', '',
             '| Condition | Status | Finding and boundary |', '| --- | --- | --- |']
    for row in data['requirements']:
        lines.append(f'| {row["id"]}: {row["explicitCondition"]} | {row["status"]} | {row["finding"]} ' + ' '.join(row['limitations']) + ' |')
    work = data['finiteRemainingWork']
    lines += ['', '## E15 remaining finite denominator', '',
              f'Core factories:90 accounted. Supplemental enum rows:{work["denominator"]}; unrecorded variants:{work["unwitnessedCount"]}.', '',
              'Status counts: `' + json.dumps(work['statusCounts'], sort_keys=True) + '`.', '',
              'Unwitnessed rows:' if work['unwitnessedIds'] else 'No unmapped declared row remains. Strong all-raw/direct-branch acceptance remains false.', '']
    lines.extend('- `' + x + '`' for x in work['unwitnessedIds'])
    lines += ['', 'Map existing actual consumer state/body/helper/effect at its stated strength first. Source/error/alias boundaries remain separate. This is not a demand for arbitrary graphs, every numeric value or an option Cartesian product.', '',
              '## Evidence boundaries', '',
              '- Historical142 geometry observations retain102PASS/40PARTIAL and188not-assessed premises. Current pure saved reevaluation is separately recorded and does not relabel the original checker execution.',
              '- New24JSON+4preparedLabelCell observations carry154 new/sensitive predicate checks;14JSON observations remainPARTIAL. Recorded19 common tests and the later1 standalone test are not falsely called one executed20-test run.',
              '- Missing text-only node/port/edge label sizes default0; no font measuring. The actual2section public chain is a positive continuity/reciprocity witness, not a synthetic positive.',
              '- Coordinate/container/endpoint and true compound witnesses satisfy distinct stated requirements; all coordinate modes x every routing x every hierarchy is not required.',
              '- Error observations, the23 prepared enum-identity ordering differences and unsupported raw callback/hyperedge boundaries are retained; no universal avoidance/optimality claim.', '',
              '- The previous931-binding baseline and its366direct/177advanced/50options/338branches storage counts retain their original execution scopes; final branch and five role-state/causal findings are a pure saved-evidence increment.', '',
              '## Strict portable check', '',
              '`python scripts/iteration/e13_e15_acceptance.py --check --root-map C:/code/py-visactor/py-elk=.`', '',
              'Tracked files are read directly; ignored raw must be an exact manifest member of options.zip, branches.zip, algorithms.zip or advanced.zip. No old checkout/test-runs fallback. `--seal-evidence` incrementally rebuilds only this additional closure, without changing the old archives.', '',
              'This does not modify iteration-plan, option ledger, role table, Source or publication state. Full details and raw SHA/pointers are in [E13_E15_ACCEPTANCE.json](E13_E15_ACCEPTANCE.json).', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--seal-evidence', action='store_true')
    p.add_argument('--root-map', action='append', default=[])
    args = p.parse_args()
    if args.check == args.seal_evidence:
        p.error('choose --check or --seal-evidence')
    if any(x.replace('\\', '/') != OLD_ROOT + '=.' for x in args.root_map):
        p.error('only the documented historical execution root to current repository mapping is accepted')
    if args.seal_evidence:
        seal()
    d = make()
    text = json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    md = markdown(d)
    if args.seal_evidence:
        (ROOT / JSON).write_text(text, encoding='utf-8', newline='\n')
        (ROOT / MD).write_text(md, encoding='utf-8', newline='\n')
    else:
        require((ROOT / JSON).read_text(encoding='utf-8') == text, 'Acceptance JSON differs')
        require((ROOT / MD).read_text(encoding='utf-8') == md, 'Acceptance Markdown differs')
    print(json.dumps({'schema': d['schema'], 'iterations': d['iterations'],
                      'remainingFiniteVariants': d['finiteRemainingWork']['unwitnessedCount'],
                      'evidenceFiles': len(d['evidence']), 'productsExecuted': 0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
