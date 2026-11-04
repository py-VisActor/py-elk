"""Independent negative controls for E09 time views and raw host receipts."""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from layout_checks import load, contract, diff
from validate_e09_coverage import (RECORD, HOST_REQUEST, decode_capture, embedded_json, unb64,
    semantic, monitor_view, validate_host_observation, validate_candidate_receipt, validate_installed_identity,
    validate_probe_receipt, validate_process_identity, b64, digest, encoded)
from audit_fixture_support import frozen_e09_root

ROOT=frozen_e09_root()


class E09CoverageAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference=load(ROOT/RECORD)
        cls.by_id={x['definition']['id']:x for x in cls.reference['cases']}

    def context(self,identifier):
        capture=self.by_id[identifier];raw=unb64(capture['requestBytesBase64']);request=embedded_json(raw)
        request['_sha']=capture['definition']['requestSha256']
        return decode_capture(capture['captures'][0]),request

    def test_generated_timing_view_keeps_raw_difference_and_business_timing_exact(self):
        original,request=self.context('reserved-object-11');expected=semantic(original,request)
        mutant=copy.deepcopy(original)
        # A zero-duration generated leaf remains legitimate; raw strict differs.
        tree=mutant['result']['logging'];old=tree['executionTime'];tree['executionTime']=0 if old else float(1000)*1e-9
        mutant['inputAfter']['logging']['executionTime']=tree['executionTime']
        request_copy=copy.deepcopy(request)
        if not old:mutant['clock']['endMs']=max(mutant['clock']['endMs'],mutant['clock']['startMs']+1)
        self.assertEqual(semantic(mutant,request_copy),expected)
        self.assertFalse(diff(contract(original),contract(mutant))['passed'])
        for location in ('root','business','node','edge'):
            with self.subTest(location=location):
                bad=copy.deepcopy(original)
                for graph in (bad['result'],bad['inputAfter']):
                    owner={'root':graph,'business':graph['business']['logging'],'node':graph['children'][0]['logging'],'edge':graph['edges'][0]['logging']}[location]
                    owner['executionTime']+=1
                self.assertNotEqual(semantic(bad,request),expected)

    def test_monitor_flags_types_clock_scale_and_nonfinite_values_fail_closed(self):
        for value in (True,float('nan'),float('inf'),10**1000,1e308,0.0000005):
            with self.subTest(value=str(value)[:20]):
                with self.assertRaises(ValueError):monitor_view({'name':'task','executionTime':value},False,True)
        for tree,logging,timing in (({'name':'task','logs':['unexpected']},False,False),
            ({'name':'task','executionTime':0},True,False),({'name':'task'},False,True),
            ({'name':'task','children':[]},False,False),({'name':'task','logs':[]},True,False)):
            with self.subTest(tree=tree):
                with self.assertRaises(ValueError):monitor_view(tree,logging,timing)
        self.assertEqual(monitor_view({'name':'task','executionTime':float(-2000)*1e-9},False,True),{'name':'task','executionTime':0})

    def test_name_order_logs_and_result_mutations_cannot_hide_as_clock_changes(self):
        original,request=self.context('layered-chain-flags-11');expected=semantic(original,request)
        for kind in ('name','phase-order','log','coordinates'):
            with self.subTest(kind=kind):
                mutant=copy.deepcopy(original)
                for graph in (mutant['result'],mutant['inputAfter']):
                    if kind=='name':graph['logging']['name']='wrong root'
                    elif kind=='phase-order':graph['logging']['children'][0]['children'].reverse()
                    elif kind=='log':graph['logging']['children'][0]['logs'][0]='fabricated modules'
                    else:graph['children'][0]['x']+=1
                try:actual=semantic(mutant,request)
                except ValueError:continue
                self.assertNotEqual(actual,expected)

    def test_installed_portable_receipt_and_host_negative_controls(self):
        value=load(ROOT/'references/e09-coverage-installed.json')
        positive=validate_candidate_receipt(value,root=ROOT)
        self.assertIs(positive['passed'],True);self.assertIs(positive['hostProbeValidated'],True)
        host=decode_capture(value['hostProbe']['captures'][0]);request=load(ROOT/HOST_REQUEST)
        self.assertIs(validate_host_observation(host,request)['passed'],True)
        for kind in ('launcher-as-spawned-child','self-parent','direct-wrong-parent'):
            with self.subTest(pidRelationship=kind):
                probe=copy.deepcopy(value['hostProbe'])
                for capture in probe['captures']:
                    raw=decode_capture(capture)
                    if kind=='launcher-as-spawned-child':
                        raw['engine']['parentPid']=value['launcherPid'];capture['command']['executionPid']=value['launcherPid']
                    elif kind=='self-parent':raw['engine']['parentPid']=raw['engine']['pid']
                    else:
                        capture['command']['executionPid']=raw['engine']['pid']
                        raw['engine']['parentPid']=value['launcherPid']+1
                        while raw['engine']['parentPid'] in (raw['engine']['pid'],value['launcherPid']):raw['engine']['parentPid']+=1
                    data=encoded(raw);capture['observationBytesBase64']=b64(data);capture['observationSha256']=digest(data)
                with self.assertRaises(ValueError):validate_probe_receipt(probe,value,'host',root=ROOT)
        self.assertTrue(validate_probe_receipt(value['hostProbe'],value,'host',root=ROOT)['passed'])
        for kind in ('error-code','boolean-state','clock-scale','business-shape','snapshot','number'):
            with self.subTest(kind=kind):
                mutant=copy.deepcopy(host)
                if kind=='error-code':mutant['publicCases'][0]['error']['code']='WRONG'
                elif kind=='boolean-state':mutant['monitorPrimitives']['state']['firstBegin']=1
                elif kind=='clock-scale':mutant['monitorPrimitives']['clocks'][0]['tree']['executionTime']=0.002
                elif kind=='business-shape':mutant['monitorPrimitives']['collect']['after']['children'].reverse()
                elif kind=='snapshot':mutant['kernelBoundaries'][0]['snapshotCalls']=38
                else:mutant['numberAdapter'][0]['string']='wrong'
                with self.assertRaises(ValueError):validate_host_observation(mutant,request)
        self.assertIs(validate_host_observation(host,request)['passed'],True)

    def test_actual_shipped_inventory_and_metadata_fail_before_layout_capture(self):
        # The geometry receipt was exported from a genuine isolated installation.
        # This check uses its raw installed identity only, not its source context
        # or a saved acceptance flag for any previous verifier version.
        installed=load(ROOT/'references/e09-installed-check.json')['installed']
        self.assertIn('DISTRIBUTION_METADATA_VALIDATED',validate_installed_identity(installed,root=ROOT)['status'])
        self.assertNotIn('model/README.md',installed['packageFilesSha256'])
        for kind in ('runtime-missing','license-missing','extra-readme','runtime-changed','metadata-rebound','source-path','relative-path','parent-traversal'):
            with self.subTest(kind=kind):
                mutant=copy.deepcopy(installed)
                if kind=='runtime-missing':del mutant['packageFilesSha256']['api.py']
                elif kind=='license-missing':del mutant['packageFilesSha256']['_licenses/NOTICE-E09.md']
                elif kind=='extra-readme':mutant['packageFilesSha256']['model/README.md']='0'*64
                elif kind=='runtime-changed':mutant['packageFilesSha256']['api.py']='0'*64
                elif kind=='source-path':mutant['modulePath']=str(ROOT/'src/pyelk')
                elif kind=='relative-path':mutant['modulePath']='pyelk'
                elif kind=='parent-traversal':mutant['modulePath']=str(ROOT/'somewhere/../src/pyelk')
                else:
                    raw=unb64(mutant['distributionMetadata']['bytesBase64'])+b'\nincorrect installed README body\n'
                    mutant['distributionMetadata']['bytesBase64']=b64(raw);mutant['distributionMetadata']['sha256']=digest(raw)
                with self.assertRaises(ValueError):validate_installed_identity(mutant,root=ROOT)
        self.assertIn('DISTRIBUTION_METADATA_VALIDATED',validate_installed_identity(installed,root=ROOT)['status'])

if __name__=='__main__':unittest.main()
