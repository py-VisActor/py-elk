"""Real offline source/approval and static branch declaration negative controls.

The shared fixture contains only the actual read closure. Every mutation first
passes its real unchanged control, then targets one meaning while rebinding
incidental hashes where necessary. No candidate receipt, Git or npm is needed.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_fixture_support import copy_files, record_reads, frozen_e09_root
from layout_checks import load
from validate_e09_sources import APPROVALS, BRANCH_MATRIX, SOURCES, check, validate_branch_matrix

# These controls certify the original bounded E09 source/declaration scope.
# Full native source and payload acceptance is a separate current-package gate.
ROOT = frozen_e09_root()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class E09SourceAndDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        source = load(ROOT / SOURCES)
        approval = load(ROOT / APPROVALS)
        matrix = load(ROOT / BRANCH_MATRIX)
        paths = {SOURCES, APPROVALS, BRANCH_MATRIX, 'UPSTREAM.json', 'docs/release-profiles.json',
                 'references/e09-metadata-schema.json', 'references/e09-host-contract.json',
                 'references/e08-metadata-schema.json', 'references/layout/suite.json', source['license']['licenseFile']}
        paths |= {'references/metadata/' + kind + '.json' for kind in ('algorithms', 'options', 'categories')}
        paths |= {row['path'] for row in approval['reviews'].values()}
        paths |= {ref['path'] for row in matrix['rows'] for ref in row['implementation'] + row['assertions']}
        paths |= {'scripts/' + row['validator'].split('.')[0] + '.py' for row in matrix['plannedEvidence'].values()}
        paths |= {row['request'] for row in matrix['masterCases']}
        cls.copy_receipt = copy_files(ROOT, cls.root, paths)
        cls.original = {name: (cls.root / name).read_bytes() for name in paths}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        for name, raw in self.original.items():
            (self.root / name).write_bytes(raw)

    def write(self, name, value):
        (self.root / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())

    def source_positive(self):
        result = check(self.root)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['approvedComponentCount'], 40)
        return result

    def branch_positive(self):
        result = validate_branch_matrix(load(self.root / BRANCH_MATRIX), root=self.root)
        self.assertTrue(result['passed'], result)
        self.assertEqual((result['requiredDeclarationCount'], result['declaredBranchCount'], result['masterCaseCount']),
                         (38, 219, 25))
        return result

    def source_negative(self, target):
        result = check(self.root)
        self.assertFalse(result['passed'], result)
        self.assertIn(target, '\n'.join(result['errors']), result)

    def branch_negative(self, target):
        result = validate_branch_matrix(load(self.root / BRANCH_MATRIX), root=self.root)
        self.assertFalse(result['passed'], result)
        self.assertIn(target, '\n'.join(result['errors']), result)

    def rebind_source(self):
        approval = load(self.root / APPROVALS)
        approval['sourceDocumentSha256'] = digest((self.root / SOURCES).read_bytes())
        self.write(APPROVALS, approval)

    def rebind_review(self, identity, review):
        approval = load(self.root / APPROVALS)
        row = approval['reviews'][identity]
        self.write(row['path'], review)
        row['sha256'] = digest((self.root / row['path']).read_bytes())
        self.write(APPROVALS, approval)

    def test_real_offline_positive_reads_only_the_complete_sparse_closure(self):
        with record_reads(self.root) as reads:
            source = self.source_positive()
            matrix = self.branch_positive()
        self.assertTrue(reads <= self.original.keys(), reads - self.original.keys())
        self.assertFalse(any('.local' in name or '.git' in name or name.startswith('test-runs/') for name in reads))
        self.assertFalse(source['runtimeAcceptanceAssessed'])
        self.assertFalse(matrix['runtimeReceiptsRead'])
        self.assertFalse((self.root / 'references/e09-installed-check.json').exists())
        self.assertFalse((self.root / 'references/e09-coverage-installed.json').exists())
        self.assertLess(self.copy_receipt['copiedFiles'], 90)

    def test_changed_raw_source_and_rebound_hashes_cannot_replace_fixed_seals(self):
        self.source_positive()
        source = load(self.root / SOURCES)
        component = source['components'][0]
        raw = base64.b64decode(component['sourceBytesBase64']).replace(b'1000', b'1001')
        self.assertNotEqual(digest(raw), component['spanSha256'])
        component['sourceBytesBase64'] = base64.b64encode(raw).decode()
        component['spanSha256'] = digest(raw)
        self.write(SOURCES, source)
        self.rebind_source()
        self.source_negative('Fixed source component seal differs')

    def test_auxiliary_api_span_rebinding_and_wrong_range_are_rejected(self):
        self.source_positive()
        source = load(self.root / SOURCES)
        api = next(row for row in source['sources'] if row['sourceId'] == 'fixed-api')
        raw = base64.b64decode(api['sourceBytesBase64']).replace(b'false', b'true ')
        self.assertNotEqual(digest(raw), api['spanSha256'])
        api['sourceBytesBase64'] = base64.b64encode(raw).decode()
        api['spanSha256'] = digest(raw)
        self.write(SOURCES, source)
        self.rebind_source()
        self.source_negative('Fixed auxiliary source span seal differs')

    def test_empty_missing_and_duplicate_components_cannot_shrink_denominator(self):
        for kind in ('empty', 'missing', 'duplicate'):
            with self.subTest(kind=kind):
                self.setUp()
                self.source_positive()
                source = load(self.root / SOURCES)
                source['components'] = ([] if kind == 'empty' else source['components'][:-1] if kind == 'missing'
                                        else source['components'][:-1] + [copy.deepcopy(source['components'][0])])
                self.write(SOURCES, source)
                self.rebind_source()
                self.source_negative('Source component denominator differs')

    def test_conventional_seconds_cpu_claim_or_clamped_clock_cannot_replace_source_formula(self):
        for field, value in [('intern47', 1000000), ('notCpuTime', False), ('formula', 'max(0,(end_ms-start_ms)/1000)')]:
            with self.subTest(field=field):
                self.setUp()
                self.source_positive()
                source = load(self.root / SOURCES)
                source['clockFacts'][field] = value
                self.write(SOURCES, source)
                self.rebind_source()
                self.source_negative('Generated wall-clock scale differs')

    def test_rejected_review_with_rebound_record_sha_cannot_approve_sources(self):
        self.source_positive()
        approval = load(self.root / APPROVALS)
        review = load(self.root / approval['reviews']['V-PROVIDER-01']['path'])
        review['accepted'] = False
        review['blockers'] = ['Deliberate rejected control']
        self.rebind_review('V-PROVIDER-01', review)
        self.source_negative('Independent source review rejected or incomplete')

    def test_reviewed_raw_material_rebinding_cannot_replace_actual_approved_span(self):
        self.source_positive()
        approval = load(self.root / APPROVALS)
        record = approval['reviews']['V-PROVIDER-01']
        review = load(self.root / record['path'])
        name = next(name for name in record['originalMaterialBytesBase64'] if name.endswith('.txt'))
        body = base64.b64decode(record['originalMaterialBytesBase64'][name]).replace(b'importGraph_1', b'importGraph_X')
        record['originalMaterialBytesBase64'][name] = base64.b64encode(body).decode()
        review['filesSha256'][name] = digest(body)
        self.write(record['path'], review)
        record['sha256'] = digest((self.root / record['path']).read_bytes())
        self.write(APPROVALS, approval)
        self.source_negative('Reviewed source span differs from component material')

    def test_bk_subset_cannot_drop_its_independent_fixed_monitor_base(self):
        self.source_positive()
        approval = load(self.root / APPROVALS)
        review = load(self.root / approval['reviews']['V-BK-01']['path'])
        review['inheritsAcceptedComponents']['sha256'] = '0' * 64
        self.rebind_review('V-BK-01', review)
        self.source_negative('Independent source subset omits its fixed monitor base review')

    def test_empty_approvals_or_rebound_scope_expansion_cannot_self_approve(self):
        for kind in ('empty-approvals', 'scope-expansion'):
            with self.subTest(kind=kind):
                self.setUp()
                self.source_positive()
                if kind == 'empty-approvals':
                    approval = load(self.root / APPROVALS)
                    approval['approvals'] = []
                    self.write(APPROVALS, approval)
                    target = 'Whole diagnostics source approval remains pending'
                else:
                    source = load(self.root / SOURCES)
                    source['components'][-1]['approvedScopeProposal'] = 'All compound and balanced algorithms approved'
                    self.write(SOURCES, source)
                    self.rebind_source()
                    target = 'Reviewed component caller/scope differs'
                self.source_negative(target)

    def test_branch_id_and_branch_enumeration_reduction_cannot_recount_to_pass(self):
        for kind in ('missing-id', 'missing-branch'):
            with self.subTest(kind=kind):
                self.setUp()
                self.branch_positive()
                matrix = load(self.root / BRANCH_MATRIX)
                if kind == 'missing-id':
                    matrix['rows'].pop()
                    matrix['requiredDeclarationCount'] -= 1
                    target = 'Branch declaration/count denominator differs'
                else:
                    matrix['rows'][0]['branches'].pop()
                    target = 'Required branch declaration differs'
                self.write(BRANCH_MATRIX, matrix)
                self.branch_negative(target)

    def test_real_symbol_and_test_assertion_must_still_exist(self):
        for reference in [('src/pyelk/api.py', 'async def knownLayoutAlgorithms(', 'async def missingLayoutAlgorithms('),
                          ('tests/api/test_e08_metadata.py', 'def test_all_query_children_are_independent_across_calls_and_instances(',
                           'def missing_all_query_children_are_independent_across_calls_and_instances(')]:
            with self.subTest(path=reference[0]):
                self.setUp()
                self.branch_positive()
                path = self.root / reference[0]
                body = path.read_text(encoding='utf-8')
                self.assertIn(reference[1], body)
                path.write_text(body.replace(reference[1], reference[2]), encoding='utf-8')
                self.branch_negative('Branch symbol missing/ambiguous')

    def test_current_profile_and_metadata_bounds_cannot_drift(self):
        for name in ('docs/release-profiles.json', 'references/e09-metadata-schema.json', 'references/e09-host-contract.json'):
            with self.subTest(path=name):
                self.setUp()
                self.branch_positive()
                value = load(self.root / name)
                if name.startswith('docs/'):
                    value['profiles'][0]['inputDomain']['originalChildNodes']['maximum'] = 9
                    target = 'Current release-profile scope/bounds differ'
                elif name.endswith('metadata-schema.json'):
                    value['expectedQueries']['default']['algorithms'][0]['native']['constraints']['originalEdges']['maximum'] = 29
                    target = 'Current metadata layout constraints differ'
                else:
                    value['loggingTrueSupported'] = False
                    target = 'Current E09 host diagnostic/denominator contract differs'
                self.write(name, value)
                self.branch_negative(target)

    def test_planned_evidence_and_master_classification_cannot_be_replaced(self):
        for kind in ('old-wheel-path', 'master-status', 'master-bytes'):
            with self.subTest(kind=kind):
                self.setUp()
                self.branch_positive()
                matrix = load(self.root / BRANCH_MATRIX)
                if kind == 'old-wheel-path':
                    matrix['plannedEvidence']['newcoverage']['path'] = 'references/e08-installed-check.json'
                    target = 'Planned same-wheel evidence paths/roles differ'
                elif kind == 'master-status':
                    matrix['masterCases'][0]['classification'] = 'out-of-scope'
                    target = 'Master request/classification differs'
                else:
                    path = self.root / matrix['masterCases'][0]['request']
                    path.write_bytes(path.read_bytes() + b'\n')
                    target = 'Master request/classification differs'
                self.write(BRANCH_MATRIX, matrix)
                self.branch_negative(target)

    def test_static_documents_cannot_promote_runtime_or_release_acceptance(self):
        for name in (SOURCES, APPROVALS, BRANCH_MATRIX):
            with self.subTest(path=name):
                self.setUp()
                self.source_positive()
                self.branch_positive()
                value = load(self.root / name)
                value['packagePublished'] = True
                self.write(name, value)
                if name == BRANCH_MATRIX:
                    self.branch_negative('Branch declarations promote runtime/release acceptance')
                else:
                    if name == SOURCES:
                        self.rebind_source()
                    self.source_negative('promote')


if __name__ == '__main__':
    unittest.main()
