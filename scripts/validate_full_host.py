"""Exercise the full public API and real native-process lifecycle.

Run after implementation is complete. Each invocation writes a new report
directory; source fingerprints belong to this execution, never an old receipt.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pyelk import ELK,ExecutionTimeoutError,QueueFullError,ResourceClosedError,ValidationError


def graph():
    return {'id':'root','business':{'preserve':[1,True,None,'原值']},
            'layoutOptions':{'algorithm':'layered','randomSeed':42},
            'children':[{'id':'a','width':30,'height':20},{'id':'b','width':30,'height':20}],
            'edges':[{'id':'ab','sources':['a'],'targets':['b']}]}


def require(value,message):
    if not value:raise AssertionError(message)


async def raises(error_type,awaitable):
    try:await awaitable
    except error_type:return
    raise AssertionError('Expected '+error_type.__name__)


async def wait_for_worker(elk):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        state=elk._controller.snapshot()
        if state['worker_alive']and any(job['progress']is not None for job in state['jobs']):
            return state
        await asyncio.sleep(.005)
    raise AssertionError('Worker did not report entry into native execution')


def long_graph():
    return {'id':'slow','layoutOptions':{'algorithm':'force','randomSeed':42,
                                        'force.iterations':100000},
            'children':[{'id':str(i),'width':20,'height':15}for i in range(80)],
            'edges':[{'id':'e'+str(i),'sources':[str(i)],'targets':[str(i+1)]}for i in range(79)]}


async def public_contract():
    original=graph();before=copy.deepcopy(original)
    with ELK(timeout=30)as elk:
        require(len(await elk.knownLayoutAlgorithms())==12,'Default algorithm count')
        require(len(await elk.knownLayoutOptions())==243,'Default option count')
        require(len(await elk.knownLayoutCategories())==8,'Default category count')
        descriptions=await elk.knownLayoutAlgorithms();descriptions[0]['id']='mutated'
        require((await elk.knownLayoutAlgorithms())[0]['id']!='mutated','Metadata alias escaped')
        first=await elk.layout(original)
        require(original==before,'Caller input was mutated')
        require(first['business']==before['business'],'Business JSON was changed')
        require(first['width']>0 and first['height']>0,'Native geometry missing')
        require(first['edges'][0].get('sections'),'Real edge routing missing')
        first_state=elk._controller.snapshot();pid=first_state['worker_pid']
        require(first_state['worker_alive'],'Successful native process was not retained')
        second=await elk.layout(original)
        require(first==second,'Seeded request changed across provider reuse')
        require(elk._controller.snapshot()['worker_pid']==pid,'Worker was not reused')
        first['business']['preserve'].append('changed')
        require(second['business']==before['business'],'Returned graphs alias each other')
        await raises(ValidationError,elk.layout({'children':[]}))
        require(elk._controller.snapshot()['worker_pid']==pid,'Validation failure discarded healthy runtime')
        recovered=await elk.layout(original)
        require(recovered==second,'Validation failure corrupted next layout')
    final=elk._controller.snapshot()
    require(not final['worker_alive']and not final['dispatcher_alive'],'Close left resources alive')
    require(all(job['reaped']for job in final['jobs']),'Closed process was not reaped')
    await raises(ResourceClosedError,elk.layout(original))
    elk.close()


async def metadata_selection():
    async with ELK({'algorithms':[]})as elk:
        require(len(await elk.knownLayoutAlgorithms())==3,'Core-only registration differs')
        result=await elk.layout({'id':'r','layoutOptions':{'algorithm':'box'},
                                 'children':[{'id':'n','width':10,'height':10}]})
        require(result['width']>0,'Core provider was not executable')


async def deep_business():
    request=graph();branch=request['payload']={}
    for index in range(1500):branch['child']={};branch=branch['child']
    branch['leaf']='retained'
    with ELK(timeout=30)as elk:result=await elk.layout(request)
    branch=result['payload']
    for _ in range(1500):branch=branch['child']
    require(branch['leaf']=='retained','Deep payload failed worker transport')


async def timeout_recovery():
    elk=ELK(timeout=.05)
    try:
        await raises(ExecutionTimeoutError,elk.layout(long_graph()))
        state=elk._controller.snapshot()
        require(not state['worker_alive'],'Timed out process still alive')
        require(all(job['reaped']for job in state['jobs']),'Timed out process not reaped')
        # The configured timeout remains a submission deadline. Use an ordinary
        # next request with a larger deadline to prove the same instance recovers.
        elk._controller._timeout=30
        require((await elk.layout(graph()))['width']>0,'Timeout poisoned next job')
    finally:elk.close()


async def cancellation_and_queue():
    elk=ELK(max_pending=2,timeout=30);active=queued=None
    try:
        active=asyncio.create_task(elk.layout(long_graph()))
        running=await wait_for_worker(elk);pid=running['worker_pid']
        queued=asyncio.create_task(elk.layout(graph()))
        await asyncio.sleep(0)
        await raises(QueueFullError,elk.layout(graph()))
        active.cancel()
        try:await active
        except asyncio.CancelledError:pass
        else:raise AssertionError('Running layout did not cancel')
        result=await queued
        require(result['width']>0,'Cancellation prevented pending request')
        state=elk._controller.snapshot()
        require(state['worker_pid']!=pid,'Cancelled native process was reused')
        require(any(job['pid']==pid and job['reaped']for job in state['jobs']),
                'Cancelled process has no actual reap record')
    finally:
        elk.close()
        for task in(active,queued):
            if task is not None:
                try:await task
                except BaseException:pass


async def close_running():
    elk=ELK(timeout=30);task=asyncio.create_task(elk.layout(long_graph()))
    try:
        await wait_for_worker(elk);elk.close()
        await raises(ResourceClosedError,task)
        state=elk._controller.snapshot()
        require(not state['worker_alive']and not state['dispatcher_alive'],'Running close leaked resources')
    finally:
        elk.close()
        try:await task
        except BaseException:pass


async def run(out):
    records=[]
    for check in(public_contract,metadata_selection,deep_business,timeout_recovery,
                 cancellation_and_queue,close_running):
        started=time.monotonic();record={'case':check.__name__}
        try:await check();record['passed']=True
        except Exception as error:
            record.update(passed=False,type=type(error).__name__,message=str(error),
                          traceback=traceback.format_exc())
        record['elapsedSeconds']=time.monotonic()-started;records.append(record)
        (out/(check.__name__+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        print(check.__name__+': '+('PASS'if record['passed']else'FAIL '+record['message']),flush=True)
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted((ROOT/'src/pyelk').rglob('*'))if p.is_file()and'__pycache__'not in p.parts}
    records=asyncio.run(run(args.out))
    report={'schema':'py-elk-full-host-validation/v1','passed':all(x['passed']for x in records),
            'sourceFilesSha256AtStart':sources,'cases':records,'fullAlgorithmAcceptance':False}
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
