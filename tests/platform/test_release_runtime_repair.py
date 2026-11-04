"""Synthetic byte-bound release-gate controls only; no product execution."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import release_readiness as gate


class RuntimeRepairReadinessTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.delta_sha='d'*64
        self.before=b'def place_nodes():\n    return 1\n'
        self.after=b'def place_nodes():\n    return 2  # synthetic reviewed repair\n'
        self.payload={gate.VERSION_MODULE:b'__version__ = "0.1.0"\n',gate.MODULE:self.after}
        self.payload.update({'pyelk/test_%03d.py'%n:b'# synthetic module\n'for n in range(194)})
        self.payload.update({'pyelk/_licenses/test_%02d.txt'%n:b'synthetic notice\n'for n in range(11)})
        self.payload['pyelk/py.typed']=b''
        for name,raw in self.payload.items():self.raw('src/'+name,raw)
        old=dict(self.payload);old[gate.VERSION_MODULE]=b'__version__ = "0.0.1a0"\n';old[gate.MODULE]=self.before
        baseline={'src/'+name:gate.digest(raw)for name,raw in old.items()}
        self.frozen={'inputFilesSha256':baseline}
        current={name:gate.digest(raw)for name,raw in self.payload.items()}
        self.error={'name':'RecursionError','message':'Synthetic reviewed active-path error','code':None,'path':None}
        review={'schema':'pyelk-runtime-repair-review/v1','repairId':gate.REPAIR_ID,'approved':True,
                'beforeModuleSha256':gate.digest(self.before),'afterModuleSha256':gate.digest(self.after),
                'expectedNativeError':self.error,'diff':self.raw('evidence/repair.diff',gate.repair_diff(self.before,self.after))}
        self.review=review;self.receipts={}
        repair={'id':gate.REPAIR_ID,'beforeModule':self.raw('evidence/before.py',self.before),
                'afterModule':{'path':'src/'+gate.MODULE,'sha256':current[gate.MODULE]},
                'review':self.document('evidence/review.json',review),'checks':{}}
        self.delta={'schema':'py-elk-release-candidate-delta/v2','validationMode':'runtime-repair',
                    'candidateVersion':'0.1.0','baselineVersion':'0.0.1a0',
                    'baselineExecutionReusedForCandidate':False,'baselineWheelSha256':gate.BASELINE_WHEEL_SHA,
                    'runtimeFilesSha256':current,'sourceOriginalSha256':baseline,
                    'changedRuntimeFiles':[gate.VERSION_MODULE,gate.MODULE],'runtimeRepair':repair}
        self.checked={'schema':'py-elk-release-candidate-delta-validation/v2','passed':True,
                      'candidateDeltaSha256':self.delta_sha,'baselineExecutionRebound':False,
                      'baselineWheelSha256':gate.BASELINE_WHEEL_SHA,'runtimeFiles':208,
                      'normalizedPythonModules':195,'changedRuntimeFiles':[gate.VERSION_MODULE,gate.MODULE],
                      'runtimeRepairModuleSha256':current[gate.MODULE],'runtimeReexecuted':True}
        for kind,key in(('cycle-termination','cycleTermination'),('valid-tree-regression','validTreeRegression')):
            request={'graph':{'id':'root','layoutOptions':{'org.eclipse.elk.algorithm':'mrtree'},
                             'children':[{'id':'node','x':1,'y':2,'width':10,'height':10}]},
                     'constructor':{},'layoutArguments':{'logging':False,'measureExecutionTime':False}}
            request_binding=self.document('evidence/'+kind+'-request.json',request)
            ref={'schema':'py-elk-layout-observation/v1','requestSha256':request_binding['sha256'],
                 'engine':{'name':'elkjs','version':'0.12.1','entrypointSha256':gate.BUNDLE_SHA},
                 'outcome':'returned','result':request['graph']}
            native={'schema':ref['schema'],'requestSha256':request_binding['sha256'],'outcome':'returned',
                    'result':request['graph'],'inputAfter':request['graph'],'constructorAfter':{},
                    'argumentsAfter':request['layoutArguments'],'termination':{'outcome':'returned'},
                    'engine':{'name':'pyelk','version':'0.1.0','sourcesUnchanged':True,
                              'sourceFilesSha256':{n.removeprefix('pyelk/'):v for n,v in current.items()if n.endswith('.py')}}}
            if kind=='cycle-termination':
                ref.update(outcome='threw',error={'name':'RangeError','message':'Maximum call stack size exceeded'})
                native.update(outcome='threw',error=self.error)
            receipt={'schema':'pyelk-runtime-repair-check/v1','repairId':gate.REPAIR_ID,'kind':kind,
                     'candidateModuleSha256':current[gate.MODULE],
                     'cases':[{'id':'synthetic-'+kind,'request':request_binding,
                               'reference':self.document('evidence/'+kind+'-reference.json',ref),
                               'native':self.document('evidence/'+kind+'-native.json',native),
                               'nativeCommand':self.document('evidence/'+kind+'-command.json',{'exitCode':0,'timedOut':False})}]}
            self.receipts[key]=receipt
            repair['checks'][key]=self.document('evidence/'+kind+'.json',receipt)

    def raw(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        return {'path':name,'sha256':gate.digest(value)}

    def document(self,name,value):return self.raw(name,(json.dumps(value,sort_keys=True)+'\n').encode())

    def check(self):return gate.validate_delta(self.root,self.frozen,self.delta,self.checked,self.delta_sha)

    def rejected(self):
        with self.assertRaises((ValueError,KeyError,FileNotFoundError)):self.check()

    def receipt_field(self,group,key,mutate):
        receipt=self.receipts[group];row=receipt['cases'][0][key]
        value=json.loads((self.root/row['path']).read_bytes());mutate(value)
        receipt['cases'][0][key]=self.document(row['path'],value)
        old=self.delta['runtimeRepair']['checks'][group]
        self.delta['runtimeRepair']['checks'][group]=self.document(old['path'],receipt)

    def test_reviewed_v2_checks_all_208_files_and_real_bound_observation_values(self):
        self.assertEqual(len(self.check()),208)

    def test_legacy_v1_version_only_remains_supported(self):
        self.raw('src/'+gate.MODULE,self.before)
        self.delta['runtimeFilesSha256'][gate.MODULE]=gate.digest(self.before)
        self.delta.update(schema='py-elk-release-candidate-delta/v1',validationMode='version-only',changedRuntimeFiles=[gate.VERSION_MODULE])
        del self.delta['runtimeRepair']
        self.checked.update(changedRuntimeFiles=[gate.VERSION_MODULE],normalizedPythonModules=196)
        self.assertEqual(len(self.check()),208)

    def test_legacy_v1_cannot_relabel_a_repair_as_version_only(self):
        self.delta.update(schema='py-elk-release-candidate-delta/v1',validationMode='version-only',changedRuntimeFiles=[gate.VERSION_MODULE])
        del self.delta['runtimeRepair'];self.checked.update(changedRuntimeFiles=[gate.VERSION_MODULE],normalizedPythonModules=196)
        self.rejected()

    def test_passed_boolean_alone_cannot_replace_raw_check(self):
        row=self.delta['runtimeRepair']['checks']['cycleTermination']
        self.delta['runtimeRepair']['checks']['cycleTermination']=self.document(row['path'],{'passed':True})
        self.rejected()

    def test_timeout_is_rejected_even_when_all_sha_bindings_are_updated(self):
        self.receipt_field('cycleTermination','nativeCommand',lambda v:v.update(timedOut=True));self.rejected()

    def test_bool_exit_code_is_not_numeric_success(self):
        self.receipt_field('cycleTermination','nativeCommand',lambda v:v.update(exitCode=False));self.rejected()

    def test_pre_repair_native_observation_is_not_rebound(self):
        self.receipt_field('cycleTermination','native',lambda v:v['engine']['sourceFilesSha256'].update({'algorithms/mrtree.py':gate.digest(self.before)}))
        self.rejected()

    def test_a_failed_whole_regression_cannot_be_a_passed_summary(self):
        self.receipt_field('validTreeRegression','native',lambda v:v['result']['children'][0].update(x=100));self.rejected()

    def test_extra_runtime_change_is_rejected(self):
        self.raw('src/pyelk/test_000.py',b'# unreviewed math\n')
        self.delta['runtimeFilesSha256']['pyelk/test_000.py']=gate.digest(b'# unreviewed math\n');self.rejected()

    def test_extra_initializer_code_is_rejected(self):
        value=b'__version__ = "0.1.0"\nUNREVIEWED = 1\n';self.raw('src/'+gate.VERSION_MODULE,value)
        self.delta['runtimeFilesSha256'][gate.VERSION_MODULE]=gate.digest(value);self.rejected()

    def test_missing_frozen_runtime_binding_is_rejected(self):
        del self.frozen['inputFilesSha256']['src/pyelk/test_000.py'];self.rejected()

    def test_missing_delta_baseline_binding_is_rejected(self):
        del self.delta['sourceOriginalSha256']['src/pyelk/test_000.py'];self.rejected()

    def test_changed_reviewed_diff_is_rejected_even_with_new_sha(self):
        self.review['diff']=self.raw('evidence/repair.diff',b'approved: true\n')
        self.delta['runtimeRepair']['review']=self.document('evidence/review.json',self.review);self.rejected()

    def test_wrong_candidate_delta_sha_is_rejected(self):
        self.checked['candidateDeltaSha256']='e'*64;self.rejected()

    def test_wrong_before_module_is_rejected(self):
        self.delta['runtimeRepair']['beforeModule']=self.raw('evidence/before.py',b'# another baseline\n');self.rejected()

    def test_missing_check_is_rejected(self):
        del self.delta['runtimeRepair']['checks']['validTreeRegression'];self.rejected()

    def test_escaping_evidence_path_is_rejected(self):
        self.delta['runtimeRepair']['beforeModule']['path']='../outside.py';self.rejected()

    def test_wrong_raw_sha_is_rejected(self):
        self.delta['runtimeRepair']['checks']['cycleTermination']['sha256']='0'*64;self.rejected()


class DistributionIdentityTests(unittest.TestCase):
    def test_historical_v1_and_v2_missing_names_mean_only_py_elk(self):
        for schema in('py-elk-release-candidate-delta/v1','py-elk-release-candidate-delta/v2'):
            with self.subTest(schema=schema):
                self.assertEqual(gate.validate_distribution({'name':'py-elk'},{'schema':schema},{},
                    ({'installedObservation':{}},{'installedObservation':{}})),'py-elk')

    def test_new_name_requires_and_accepts_all_explicit_observed_identities(self):
        name='py-visactor-elk'
        self.assertEqual(gate.validate_distribution({'name':name},{'distributionName':name},
            {'distributionName':name},({'distributionName':name,'installedObservation':{'distributionName':name}},)),name)

    def test_old_install_cannot_certify_new_distribution(self):
        name='py-visactor-elk'
        with self.assertRaises(ValueError):gate.validate_distribution({'name':name},{'distributionName':name},
            {'distributionName':name},({'installedObservation':{}},))

    def test_summary_name_does_not_replace_installed_identity(self):
        name='py-visactor-elk'
        with self.assertRaises(ValueError):gate.validate_distribution({'name':name},{'distributionName':name},
            {'distributionName':name},({'distributionName':name,'installedObservation':{}},))

    def test_project_and_checked_names_cannot_drift(self):
        with self.assertRaises(ValueError):gate.validate_distribution({'name':'py-elk'},
            {'distributionName':'py-visactor-elk'},{'distributionName':'py-visactor-elk'})
        with self.assertRaises(ValueError):gate.validate_distribution({'name':'py-visactor-elk'},
            {'distributionName':'py-visactor-elk'},{})

    def test_unapproved_name_and_module_namespace_are_not_distribution_identity(self):
        with self.assertRaises(ValueError):gate.validate_distribution({'name':'pyelk'},
            {'distributionName':'pyelk'},{'distributionName':'pyelk'})
        with self.assertRaises(ValueError):gate.validate_distribution({'name':'another-project'},
            {'distributionName':'another-project'},{'distributionName':'another-project'})


if __name__=='__main__':unittest.main()
