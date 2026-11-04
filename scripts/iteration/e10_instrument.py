"""Pure E10 instrumentation checks against the separate public raw samples.

Nested wall/CPU spans are explanatory costs, excluded from public statistics.
This checker never launches a worker or rewrites an execution dependency hash.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e10

COLLECTOR='tools/platform/instrument_e10.py'
PUBLIC_COLLECTOR='tools/platform/benchmark_e10.py'


def validate(value,public,root=ROOT):
    root=Path(root)
    try:
        e10.require(value['schema']=='py-elk-e10-instrumented-run/v1' and value['fullValidation'] is False,
                    'Unknown instrumented receipt or full validation claim')
        e10.require(public['schema']=='py-elk-e10-benchmark-run/v1' and public['fullValidation'] is False,
                    'Original public benchmark receipt required')
        collector_sha=e10.sha256(root/COLLECTOR)
        e10.require(value['collectorSha256']==collector_sha,'Instrumented capture source bytes changed')
        definitions=e10.load(root/'tests/fixtures/suites/E10/benchmark.json')['cases']
        e10.require([row['caseId'] for row in value['captures']]==[row['id'] for row in definitions],
                    'Expected one instrumented observation for each fixed size')
        reports=[]
        for row in value['captures']:
            command=e10.check_command(row)
            raw=e10.raw64(row['observationBytesBase64'])
            e10.require(e10.digest(raw)==row['observationSha256'],'Original instrumented observation bytes differ')
            body=e10.embedded_json(raw)
            e10.require(body['schema']=='py-elk-e10-instrumented-observation/v1' and
                        body['mode']=='instrumented' and body['fullValidation'] is False,
                        'Instrumented observation role differs')
            observed=body['observation'];worker_raw=e10.raw64(body['workerBytesBase64'])
            e10.require(e10.digest(worker_raw)==body['workerSha256'],'Original worker sidecar bytes differ')
            worker=e10.embedded_json(worker_raw)
            e10.require(worker['schema']=='py-elk-e10-worker-intervals/v1' and
                        type(worker['pid']) is int and worker['pid']>0 and
                        worker['pid']==observed['worker']['pid'] and observed['mode']=='instrumented',
                        'Worker sidecar does not belong to actual instrumented worker')
            e10.validate_process_identity(observed['engine'],{'executionPid':command['pid']},value['launcherPid'])
            e10.require(observed['executionDependencies'][COLLECTOR]==collector_sha and
                        observed['executionDependencies'][PUBLIC_COLLECTOR]==e10.sha256(root/PUBLIC_COLLECTOR),
                        'Actual instrumented execution source bytes differ')
            original=next(r for r in public['captures'] if r['caseId']==row['caseId'] and r['sample']==0)
            public_raw=e10.raw64(original['observationBytesBase64'])
            e10.require(e10.digest(public_raw)==original['observationSha256'],'Original public comparison bytes differ')
            expected=e10.embedded_json(public_raw)
            for key in ('requestBytesBase64','requestSha256','inputBefore','inputAfter','constructorBefore',
                        'constructorAfter','argumentsBefore','argumentsAfter','result','traceSummary'):
                e10.exact(observed[key],expected[key],'Instrumented/public actual '+key+' differs')
            e10.require(worker['clocks']=={'elapsed':'time.perf_counter_ns','cpu':'time.process_time_ns'},
                        'Instrumented clock units differ')
            spans=worker['spans']
            e10.require(len(spans)==25 and all(type(s['id']) is int for s in spans) and
                        [s['id'] for s in spans]==list(range(25)),'Expected 25 uniquely ordered actual spans')
            for span in spans:
                e10.require(all(type(span[k]) is int and span[k]>=0 for k in
                                ('startNs','finishNs','startCpuNs','finishCpuNs')) and
                            span['startNs']<=span['finishNs'] and span['startCpuNs']<=span['finishCpuNs'],
                            'Invalid wall/CPU nanosecond interval')
                parent_id=span['parentSpanId']
                if parent_id is not None:
                    e10.require(type(parent_id) is int and 0<=parent_id<span['id'],'Invalid parent span identity')
                    parent=spans[parent_id]
                    for start,finish in (('startNs','finishNs'),('startCpuNs','finishCpuNs')):
                        e10.require(parent[start]<=span[start]<=span[finish]<=parent[finish],
                                    'Child interval is not contained by its actual parent')
            e10.require(all(sum(s['name']==name for s in spans)==1 for name in
                            ('import_raw_graph','export_layout','Orthogonal edge routing')),
                        'Expected actual import/export/routing boundaries missing or duplicated')
            whole_id=worker['workerSpanId']
            e10.require(type(whole_id) is int and 0<=whole_id<len(spans),'Invalid whole worker span')
            whole=spans[whole_id]
            e10.require(whole['kind']=='worker' and whole['name']=='original run_job' and whole['parentSpanId'] is None,
                        'Whole worker span role differs')
            reports.append({'caseId':row['caseId'],'spanCount':len(spans),
                            'workerElapsedSeconds':(whole['finishNs']-whole['startNs'])/1e9,
                            'workerCpuSeconds':(whole['finishCpuNs']-whole['startCpuNs'])/1e9,
                            'resultAndTraceExact':True,'nestedIntervalsContained':True})
        return {'passed':True,'errors':[],'cases':reports,'fullValidation':False,'runtimeReexecuted':False,
                'historicalExecutionAuthenticated':False,
                'limitation':'Nested intervals overlap, including routing within phases. Do not sum parent/child costs or include these instrumented observations in public throughput statistics. Public receipt acceptance is checked separately.'}
    except (ValueError,KeyError,TypeError,AttributeError,OSError,IndexError,OverflowError,StopIteration) as error:
        return {'passed':False,'errors':[str(error)],'fullValidation':False,'runtimeReexecuted':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt',type=Path);parser.add_argument('--public',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    result=validate(e10.load(args.receipt),e10.load(args.public))
    result.update(receiptSha256=e10.sha256(args.receipt),publicReceiptSha256=e10.sha256(args.public),
                  verifierSha256=e10.sha256(Path(__file__)),platformVerifierSha256=e10.sha256(Path(e10.__file__)))
    from layout_checks import write
    write(args.out,result);print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
