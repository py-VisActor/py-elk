"""Targeted E08 guards: pristine positives first, then one semantic mutation."""
import base64
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import validate_e08_api as api
from layout_checks import load


class E08ApiValidationControls(unittest.TestCase):
    def fixture(self,identity='initial-default'):
        case=next(c for c in api.definitions()['cases'] if c['id']==identity)
        request=load(ROOT/api.SUITE/case['request'])
        events=load(ROOT/api.SUITE/'oracle/observations'/identity/'repeat-0/observation.json')['events']
        api.validate_reference_events(case,request,events)
        return case,request,copy.deepcopy(events)

    def rejected(self,mutation,expected,identity='initial-default'):
        case,request,events=self.fixture(identity);mutation(events)
        with self.assertRaisesRegex(ValueError,expected):api.validate_reference_events(case,request,events)

    def test_successful_wrong_or_empty_layout_is_not_just_a_dict(self):
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='layout').update(result={}), 'complete layout')

    def test_original_input_side_effects_and_call_arguments_are_required(self):
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='layout')['graphAfter'].update(id='WRONG'),'complete layout')
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='layout').update(argumentsAfter={'invented':1}),'API data field denominator|complete layout')

    def test_public_error_type_message_and_promise_style_are_separate_guards(self):
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='layout')['error'].update(name='UnsupportedFeatureError'),'public error', 'sequence-unknown-algorithm')
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='layout').update(returnKind='synchronous_throw'),'synchronous/Promise','sequence-unknown-algorithm')

    def test_metadata_fields_and_registration_order_cannot_be_rebound(self):
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='knownLayoutAlgorithms')['result'].reverse(),'ID order')
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='knownLayoutOptions')['result'][0].update(description='invented'),'fields differ')

    def test_generated_reference_clocks_remain_finite_and_same_graph_consistent(self):
        for invalid in (-1,True,10**1000):
            with self.subTest(invalid=str(invalid)[:25]):
                self.rejected(lambda es:next(e for e in es if e.get('operation')=='layout')['result']['logging'].update(executionTime=invalid),'logging duration','alias-timing-true')
        self.rejected(lambda es:next(e for e in es if e.get('operation')=='layout')['result']['logging'].update(executionTime=123),'same mutated FakeWorker graph','alias-timing-true')

    def test_empty_events_and_repeats_are_never_success(self):
        case,request,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'event denominator'):api.validate_reference_events(case,request,[])
        value={'schema':'py-elk-e08-native-runtime-receipt/v1','requestBytesBase64':base64.b64encode((ROOT/api.NATIVE_REQUEST).read_bytes()).decode(),'repeat':0,'captures':[]}
        with self.assertRaisesRegex(ValueError,'repeat denominator'):api.validate_candidate_receipt(value)

    def test_os_exit_and_idle_resource_proofs_reject_bool_or_alive_forgery(self):
        api._os_pid({'method':'OpenProcess/GetExitCodeProcess','pid':123,'opened':True,'exitCode':259,'alive':True},True)
        with self.assertRaisesRegex(ValueError,'exit-code'):api._os_pid({'method':'OpenProcess/GetExitCodeProcess','pid':123,'opened':True,'exitCode':False,'alive':True},True)
        idle={'pending':0,'running':None,'queued':[],'worker_pid':None,'worker_alive':False,'dispatcher_alive':False}
        api._idle(idle)
        for changed in ({'pending':False},{'worker_alive':True},{'dispatcher_alive':True},{'worker_pid':123}):
            with self.subTest(changed=changed),self.assertRaisesRegex(ValueError,'released'):api._idle({**idle,**changed})

    def test_strict_raw_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for raw in (b'{"state":1,"state":2}',b'{"state":NaN}',b'{"state":1e999}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):api.embedded_json(raw)

    def test_snapshot_typed_ids_exit_status_and_monotonic_lifecycle_are_required(self):
        interval={'started':1,'finished':5}
        snapshot={'state':'open','pending':0,'queued':[],'running':None,'worker_pid':None,'worker_alive':False,'dispatcher_alive':False,
                  'last_submitted_id':1,'jobs':[{'job_id':1,'state':'returned','pid':123,'exitcode':0,'reaped':True,'submitted_at':1.5,
                  'started_at':2,'finished_at':3,'progress':{'index':18,'processor':api.NATIVE_PROCESSORS[18],
                  'previous_processor':api.NATIVE_PROCESSORS[17],'previous_outcome':'returned','process_time':0.25}}]}
        api.validate_snapshot(snapshot,interval)
        for change in ({'exitcode':23},{'exitcode':False},{'job_id':True},{'reaped':False},{'started_at':4},{'finished_at':float('inf')}):
            mutated=copy.deepcopy(snapshot);mutated['jobs'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):api.validate_snapshot(mutated,interval)
        cancelled=copy.deepcopy(snapshot);cancelled['jobs'][0]['state']='cancelled'
        api.validate_snapshot(cancelled,interval)  # completion may lose publication to cancellation even after exit0

    def test_native_same_body_different_encoding_has_one_canonical_identity(self):
        original={'engine':{'pid':123,'parentPid':100},'captureInterval':{'started':1.5,'finished':2.5}}
        a=json.dumps(original,separators=(',',':')).encode();b=json.dumps(original,indent=4).encode()
        self.assertNotEqual(a,b)
        second={'engine':{'pid':124,'parentPid':100},'captureInterval':{'started':3,'finished':4}}
        api.validate_observation_independence([original,second],100)
        with self.assertRaisesRegex(ValueError,'canonical observation body'):
            api.validate_observation_independence([api.embedded_json(a),api.embedded_json(b)],100)
        second['captureInterval']['started']=2
        with self.assertRaisesRegex(ValueError,'overlap/replay'):api.validate_observation_independence([original,second],100)
        for fake in ({'pathEmpty':1,'overridesAbsent':True},{'pathEmpty':True,'overridesAbsent':1}):
            with self.assertRaises(ValueError):api.equal(fake,{'pathEmpty':True,'overridesAbsent':True},'Typed environment policy')


if __name__=='__main__':unittest.main()
