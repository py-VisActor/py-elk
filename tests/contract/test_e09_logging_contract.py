"""Public diagnostics checked against fixed official observations, not itself."""
import copy
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
if not sys.flags.isolated:sys.path.insert(0,str(ROOT/'src'))
from pyelk import ELK
from pyelk._errors import OptionValidationError
from layout_checks import load
from validate_e09_coverage import RECORD, SUITE, REFERENCE_ERRORS, decode_capture, unb64, digest, compare_case


# The frozen E09 receipts retain the former bounded adapter's /local paths
# and INVALID_GRAPH code. Full import reports the actual owned element path;
# the unknown-algorithm message is the independently captured source message.
# These are explicit Python validation categories (ADR0007/0008), not renamed
# JS error classes, and no historical request/oracle/error policy is rewritten.
FULL_HOST_ERRORS = {
    'error-unknown-endpoint': ('ModelValidationError', 'UNKNOWN_ENDPOINT', '/edges/0/targets/0',
                               'Referenced node or port does not exist'),
    'error-unknown-algorithm': ('UnknownAlgorithmError', 'UNKNOWN_ALGORITHM', '',
                                REFERENCE_ERRORS['error-unknown-algorithm']),
    'error-missing-graph': ('ModelValidationError', 'INVALID_ELEMENT', '', 'Expected a JSON object'),
}


class E09LoggingContractTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference={x['definition']['id']:x for x in load(ROOT/RECORD)['cases']}

    async def observation(self,request_bytes):
        import json
        request=json.loads(request_bytes);graph=copy.deepcopy(request['graph']);options=copy.deepcopy(request['constructor']);args=copy.deepcopy(request['layoutArguments'])
        result={'schema':'py-elk-layout-observation/v1','requestSha256':digest(request_bytes),'engine':{'name':'pyelk'},
            'inputBefore':copy.deepcopy(graph),'constructorBefore':copy.deepcopy(options),'argumentsBefore':copy.deepcopy(args),
            'clock':{'startMs':time.time_ns()//1_000_000}}
        elk=ELK(options)
        try:result.update(outcome='returned',result=await elk.layout(graph,args))
        except Exception as error:result.update(outcome='threw',error={'name':type(error).__name__,'message':str(error)},
            errorDetails={k:getattr(error,k,None) for k in ('code','path','message')})
        finally:elk.terminateWorker()
        result['clock']['endMs']=time.time_ns()//1_000_000
        result.update(inputAfter=graph,constructorAfter=options,argumentsAfter=args,termination={'outcome':'returned'})
        return result

    async def test_four_flags_preserve_business_fields_and_match_fixed_source_tree(self):
        for suffix in ('00','10','01','11'):
            with self.subTest(flags=suffix):
                captured=self.reference['reserved-object-'+suffix];raw=unb64(captured['requestBytesBase64'])
                observed=await self.observation(raw)
                result=compare_case(captured['definition'],raw,decode_capture(captured['captures'][0]),observed)
                self.assertIs(result['passed'],True)
                self.assertEqual(observed['result']['executionTime'],321)
                self.assertEqual(observed['result']['business']['logging']['executionTime'],765)
                self.assertEqual(observed['result']['children'][0]['logging']['executionTime'],123)
                self.assertEqual(observed['result']['edges'][0]['logging']['executionTime'],456)

    async def test_all_three_negative_master_cases_keep_named_host_error_contract(self):
        for identifier in ('error-unknown-endpoint','error-unknown-algorithm','error-missing-graph'):
            with self.subTest(case=identifier):
                captured=self.reference[identifier];raw=unb64(captured['requestBytesBase64']);observed=await self.observation(raw)
                reference=decode_capture(captured['captures'][0])
                self.assertEqual(reference['outcome'],'threw')
                self.assertEqual(reference['error']['message'],REFERENCE_ERRORS[identifier])
                name,code,path,message=FULL_HOST_ERRORS[identifier]
                self.assertEqual(observed['outcome'],'threw')
                self.assertEqual(observed['errorDetails'],{'code':code,'path':path,'message':message})
                self.assertEqual(observed['error'],{'name':name,'message':code+' at '+(path or '/')+': '+message})
                self.assertNotEqual(observed['error'],reference['error'])
                for key in ('input','constructor','arguments'):
                    self.assertEqual(observed[key+'Before'],observed[key+'After'])

    async def test_boolean_like_values_do_not_silently_enable_diagnostics(self):
        request=load(ROOT/SUITE/'host-checks.json')
        checked=[]
        for definition in request['publicCases']:
            if not definition['id'].startswith(('logging-','measureExecutionTime-')):continue
            with self.subTest(case=definition['id']):
                elk=ELK();data=copy.deepcopy(definition['request'])
                before=copy.deepcopy(data)
                try:
                    with self.assertRaises(OptionValidationError) as caught:await elk.layout(data['graph'],data['layoutArguments'])
                finally:elk.terminateWorker()
                error=caught.exception
                flag='measureExecutionTime' if definition['id'].startswith('measureExecutionTime-') else 'logging'
                # ADR0008 requires actual bool, so 0/1/text/null remain rejected.
                # A malformed supported flag is a typed option error in the
                # complete host, rather than an unsupported slice capability.
                self.assertEqual({'name':type(error).__name__,**{k:getattr(error,k,None) for k in ('code','path','message')}},
                    {'name':'OptionValidationError','code':'INVALID_OPTION_VALUE',
                     'path':'/layoutArguments/'+flag,'message':'Expected a Boolean'})
                self.assertEqual(data,before)
                self.assertEqual(elk.last_trace,[])
                checked.append(definition['id'])
        self.assertEqual(set(checked),{flag+'-'+value for flag in ('logging','measureExecutionTime') for value in ('zero','one','text','null')})
        self.assertEqual(len(checked),8)

if __name__=='__main__':unittest.main()
