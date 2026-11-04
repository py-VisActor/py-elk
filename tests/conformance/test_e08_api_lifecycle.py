"""Independent real native lifecycle probes; synthetic waits are not CPU proof.

The same helpers run in a genuinely installed -I interpreter. Importing this
module does not insert src; only source unittest setup explicitly does that.
"""
from __future__ import annotations
import asyncio
import copy
import ctypes
import hashlib
import importlib
import json
import os
import signal
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/reference'))
from native_process_probe import cpu_graph as native_cpu_graph,wait_for_cpu


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def pid_probe(pid):
    if os.name=='nt':
        from ctypes import wintypes
        dll=ctypes.WinDLL('kernel32',use_last_error=True)
        dll.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];dll.OpenProcess.restype=wintypes.HANDLE
        dll.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];dll.GetExitCodeProcess.restype=wintypes.BOOL
        dll.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=dll.OpenProcess(0x1000,False,pid)
        if not handle:
            error=ctypes.get_last_error()
            if error not in (87,1168):raise RuntimeError('Cannot establish PID state: '+str(error))
            return {'method':'OpenProcess/GetExitCodeProcess','pid':pid,'opened':False,'error':error,'alive':False}
        code=wintypes.DWORD()
        try:
            if not dll.GetExitCodeProcess(handle,ctypes.byref(code)):raise ctypes.WinError(ctypes.get_last_error())
            return {'method':'OpenProcess/GetExitCodeProcess','pid':pid,'opened':True,'exitCode':code.value,'alive':code.value==259}
        finally:dll.CloseHandle(handle)
    try:os.kill(pid,0)
    except ProcessLookupError:return {'method':'kill(pid,0)','pid':pid,'error':'ESRCH','alive':False}
    return {'method':'kill(pid,0)','pid':pid,'error':None,'alive':True}


def error_record(error):
    return {'type':type(error).__name__,'code':getattr(error,'code',None),
            'path':getattr(error,'path',None),'message':getattr(error,'message',str(error))}


async def wait_for(instance,predicate,timeout=15):
    deadline=time.monotonic()+timeout
    while True:
        snapshot=instance._controller.snapshot()
        if predicate(snapshot):return snapshot
        if time.monotonic()>deadline:raise AssertionError('Timed out waiting for real execution state: '+str(snapshot))
        await asyncio.sleep(0.001)


async def metadata_probe(ELK):
    first,empty=ELK(),ELK({'algorithms':[]})
    result={}
    try:
        for name,instance in [('default',first),('algorithmsEmpty',empty)]:
            result[name]={}
            for method,kind in [('knownLayoutAlgorithms','algorithms'),('knownLayoutOptions','options'),('knownLayoutCategories','categories')]:
                value=await getattr(instance,method)();result[name][kind]=copy.deepcopy(value)
                if value:
                    value[0]['id']='V_MUTATION'
                    for key in ('knownOptions','knownLayouters','targets'):
                        if isinstance(value[0].get(key),list):value[0][key].append('V_NESTED_MUTATION')
                    value.append({'id':'V_INJECTED'})
                result[name][kind+'AfterMutation']=await getattr(instance,method)()
        result['defaultAfterEmpty']=await first.knownLayoutAlgorithms()
        try:await empty.layout({'id':'not-registered'})
        except Exception as error:result['emptyLayoutError']=error_record(error)
        else:raise AssertionError('Metadata-only instance accepted layout')
        first.terminateWorker();empty.terminateWorker()
        result['closedErrors']={}
        for method in ('knownLayoutAlgorithms','knownLayoutOptions','knownLayoutCategories'):
            try:await getattr(first,method)()
            except Exception as error:result['closedErrors'][method]=error_record(error)
            else:raise AssertionError('Closed query returned')
        return result
    finally:first.terminateWorker();empty.terminateWorker()


async def public_error_probe(ELK,request):
    records={}
    for name,options in [('constructorUnknown',{'algorithms':['V_UNKNOWN']}),('constructorUnsupported',{'algorithms':['stress']}),
                         ('constructorContainer',{'algorithms':17}),('constructorWorker',{'workerFactory':None})]:
        try:instance=ELK(options)
        except Exception as error:records[name]=error_record(error)
        else:
            instance.terminateWorker();raise AssertionError('Invalid constructor accepted: '+name)
    for name,constructor,args in [('globalUnknownLocalValid',{'defaultLayoutOptions':{'elk.algorithm':'V_UNKNOWN'}},{}),
                                   ('globalUnsupportedLocalValid',{'defaultLayoutOptions':{'elk.algorithm':'stress'}},{}),
                                   # E09 implements true; keep these negative
                                   # type branches with non-bool inputs.
                                   ('logging',{}, {'logging':0}),('timing',{}, {'measureExecutionTime':0})]:
        instance=ELK(constructor);graph=copy.deepcopy(request['smallRequest']['graph']);before=fingerprint((graph,args))
        try:
            try:await instance.layout(graph,args)
            except Exception as error:records[name]=error_record(error)
            else:raise AssertionError('Invalid call accepted: '+name)
            assert before==fingerprint((graph,args)),'Error path modified caller input'
        finally:instance.terminateWorker()
    instance=ELK({'defaultLayoutOptions':{'elk.algorithm':'V_UNKNOWN'}})
    try:records['emptyCallReplacesBadConstructor']=await instance.layout(copy.deepcopy(request['smallRequest']['graph']),{'layoutOptions':{}})
    finally:instance.terminateWorker()
    return records


async def cpu_cancel_probe(ELK,request):
    instance=ELK(max_pending=2);graph=native_cpu_graph();before=fingerprint(graph)
    task=asyncio.create_task(instance.layout(graph))
    try:
        interval=await wait_for_cpu(instance,task,timeout=request['progressTimeoutSeconds'])
        events=interval['observations'];heartbeats=interval['heartbeats']
        job=events[-1]['snapshot']['jobs'][-1];pid=job['pid'];alive=pid_probe(pid)
        assert alive['alive']and events[-1]['cpuSeconds']>events[0]['cpuSeconds']
        cancelled_at=time.monotonic();task.cancel()
        try:await task
        except asyncio.CancelledError:pass
        else:raise AssertionError('Actual pending native job was not cancelled')
        after=instance._controller.snapshot();dead=pid_probe(pid)
        assert not dead['alive'] and after['pending']==0 and not after['worker_alive'] and not after['dispatcher_alive']
        small=request['smallRequest'];result=await instance.layout(copy.deepcopy(small['graph']),copy.deepcopy(small['layoutArguments']))
        recovered_idle=await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
        return {'cpuObservations':events,'heartbeats':heartbeats,'cancelRequestedAt':cancelled_at,'taskDoneBeforeCancel':False,
                'pidBeforeCancel':alive,'pidAfterCancel':dead,'afterCancel':after,'afterRecovery':recovered_idle,
                'recoveryResult':result,'traceAfterRecovery':instance.last_trace,
                'inputBeforeSha256':before,'inputAfterSha256':fingerprint(graph)}
    finally:
        if not task.done():
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
        instance.terminateWorker()


async def queue_probe(ELK,request):
    instance=ELK(max_pending=2);small=request['smallRequest'];first=asyncio.create_task(instance.layout(copy.deepcopy(request['cpuGraph'])))
    second=None
    try:
        started=await wait_for(instance,lambda s:s['running'] is not None)
        second=asyncio.create_task(instance.layout(copy.deepcopy(small['graph']),copy.deepcopy(small['layoutArguments'])))
        queued=await wait_for(instance,lambda s:bool(s['queued']))
        try:await instance.layout(copy.deepcopy(small['graph']))
        except Exception as error:full=error_record(error)
        else:raise AssertionError('Capacity overflow accepted')
        queued_id=queued['queued'][0];second.cancel()
        try:await second
        except asyncio.CancelledError:pass
        else:raise AssertionError('Queued cancellation did not propagate')
        after_queued=instance._controller.snapshot()
        await first
        final=await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
        return {'started':started,'queued':queued,'queuedJobId':queued_id,'queueFullError':full,
                'afterQueuedCancel':after_queued,'afterFirstReturn':final,'lastTrace':instance.last_trace}
    finally:
        for task in (second,first):
            if task is not None and not task.done():
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass
        instance.terminateWorker()


async def fifo_recovery_close_probe(ELK,request):
    instance=ELK();small=request['smallRequest'];graph=small['graph'];jobs=[]
    try:
        one,two=asyncio.create_task(instance.layout(copy.deepcopy(graph))),asyncio.create_task(instance.layout(copy.deepcopy(graph)))
        result1,result2=await asyncio.gather(one,two)
        fifo=instance._controller.snapshot()
        invalid=copy.deepcopy(graph);invalid['edges'][0]['targets']=['MISSING']
        try:await instance.layout(invalid)
        except Exception as error:failure=error_record(error)
        else:raise AssertionError('Missing endpoint accepted')
        trace_after_failure=instance.last_trace
        recovered=await instance.layout(copy.deepcopy(graph),copy.deepcopy(small['layoutArguments']))
        trace=instance.last_trace;trace[0]['processor']='V_MUTATION';trace_again=instance.last_trace
        final=await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
        instance.terminateWorker();closed=instance._controller.snapshot();instance.terminateWorker()
        try:await instance.layout(copy.deepcopy(graph))
        except Exception as error:closed_error=error_record(error)
        else:raise AssertionError('Closed layout accepted')
        return {'fifo':fifo,'fifoResults':[result1,result2],'validationError':failure,'traceAfterFailure':trace_after_failure,
                'recoveryResult':recovered,'traceAfterCallerMutation':trace_again,'idleBeforeClose':final,
                'closed':closed,'closedError':closed_error}
    finally:instance.terminateWorker()


def stop_pid(pid):
    if os.name=='nt':
        from ctypes import wintypes
        dll=ctypes.WinDLL('kernel32',use_last_error=True)
        dll.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];dll.OpenProcess.restype=wintypes.HANDLE
        dll.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];dll.TerminateProcess.restype=wintypes.BOOL
        dll.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=dll.OpenProcess(1,False,pid)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not dll.TerminateProcess(handle,71):raise ctypes.WinError(ctypes.get_last_error())
        finally:dll.CloseHandle(handle)
        return {'method':'TerminateProcess','pid':pid,'exitCodeRequested':71}
    os.kill(pid,signal.SIGKILL)
    return {'method':'kill(SIGKILL)','pid':pid,'signal':int(signal.SIGKILL)}


async def active_close_crash_timeout_probe(ELK,request):
    result={};small=request['smallRequest']
    for action in ('close','externalCrash'):
        instance=ELK();task=asyncio.create_task(instance.layout(native_cpu_graph()))
        try:
            interval=await wait_for_cpu(instance,task)
            running=interval['snapshots'][-1]
            assert not task.done(),'Native job completed before requested resource action'
            pid=running['worker_pid'];before=pid_probe(pid);assert before['alive']
            stop={'method':'terminateWorker'} if action=='close' else stop_pid(pid)
            if action=='close':instance.terminateWorker()
            try:await task
            except Exception as e:error=error_record(e)
            else:raise AssertionError('Interrupted native worker returned successfully')
            idle=await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
            row={'running':running,'taskDoneBeforeAction':False,'osPidBefore':before,'action':stop,'error':error,'after':idle,'osPidAfter':pid_probe(pid),'lastTrace':instance.last_trace}
            if action=='externalCrash':
                row['recoveryResult']=await instance.layout(copy.deepcopy(small['graph']),copy.deepcopy(small['layoutArguments']))
                row['afterRecovery']=await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
            result[action]=row
        finally:instance.terminateWorker()
    instance=ELK(timeout=0.001)
    try:
        started=time.monotonic()
        try:await instance.layout(copy.deepcopy(small['graph']))
        except Exception as e:error=error_record(e)
        else:raise AssertionError('Submission/startup deadline was not enforced')
        idle=await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
        result['timeout']={'timeoutSeconds':0.001,'elapsedSeconds':time.monotonic()-started,'error':error,'after':idle,
                           'osPidsAfter':[pid_probe(j['pid']) for j in idle['jobs'] if j['pid'] is not None],
                           'scope':'actual submission/startup deadline; not a claim of phase-running CPU timeout'}
    finally:instance.terminateWorker()
    return result


async def overlap_loop_probe(ELK,request):
    one,two=ELK(),ELK();tasks=[asyncio.create_task(instance.layout(native_cpu_graph())) for instance in (one,two)]
    try:
        intervals=await asyncio.gather(*(wait_for_cpu(instance,task)for instance,task in zip((one,two),tasks)))
        snapshots=[interval['snapshots'][-1]for interval in intervals]
        assert not any(t.done() for t in tasks)
        overlap={'snapshots':snapshots,'osPids':[pid_probe(s['worker_pid']) for s in snapshots], 'tasksDone':[t.done() for t in tasks]}
        assert all(p['alive'] for p in overlap['osPids'])
        await asyncio.gather(*tasks)
        overlap['after']=[await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive']) for instance in (one,two)]
    finally:
        one.terminateWorker();two.terminateWorker()
    instance=ELK();small=request['smallRequest'];task=asyncio.create_task(instance.layout(native_cpu_graph()))
    try:
        running=await wait_for(instance,lambda s:s['running'] is not None)
        async def other_loop():return await instance.layout(copy.deepcopy(small['graph']))
        try:await asyncio.to_thread(lambda:asyncio.run(other_loop()))
        except Exception as e:conflict=error_record(e)
        else:raise AssertionError('Active cross-loop work was accepted')
        await task;await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
        rebound=await asyncio.to_thread(lambda:asyncio.run(other_loop()))
        await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
        again=await instance.layout(copy.deepcopy(small['graph']))
        idle=await wait_for(instance,lambda s:s['pending']==0 and not s['dispatcher_alive'])
        return {'overlap':overlap,'crossLoop':{'running':running,'error':conflict,'otherLoopResult':rebound,'originalLoopResult':again,'after':idle}}
    finally:instance.terminateWorker()


async def capture_lifecycle(ELK,request):
    return {'metadata':await metadata_probe(ELK),'publicErrors':await public_error_probe(ELK,request),'cpuCancel':await cpu_cancel_probe(ELK,request),
            'queue':await queue_probe(ELK,request),'fifoRecoveryClose':await fifo_recovery_close_probe(ELK,request),
            'resourceActions':await active_close_crash_timeout_probe(ELK,request),'overlapAndLoop':await overlap_loop_probe(ELK,request)}


class E08IndependentLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/'src'))
        cls.ELK=importlib.import_module('pyelk').ELK
        cls.request=json.loads((ROOT/'tests/fixtures/suites/E08-api/native-request.json').read_text(encoding='utf-8'))

    def test_real_cpu_progress_heartbeat_cancel_reap_and_recovery(self):
        result=asyncio.run(cpu_cancel_probe(self.ELK,self.request))
        self.assertEqual(result['inputBeforeSha256'],result['inputAfterSha256'])

    def test_actual_queued_cancel_capacity_and_trace_publication(self):
        result=asyncio.run(queue_probe(self.ELK,self.request));self.assertEqual(result['queueFullError']['code'],'QUEUE_FULL')
        cancelled=next(j for j in result['afterFirstReturn']['jobs'] if j['job_id']==result['queuedJobId'])
        self.assertEqual((cancelled['state'],cancelled['pid'],cancelled['started_at']),('cancelled',None,None))
        self.assertEqual(result['lastTrace'],[])

    def test_actual_fifo_failure_recovery_closed_and_trace_copy(self):
        result=asyncio.run(fifo_recovery_close_probe(self.ELK,self.request));jobs=result['fifo']['jobs']
        self.assertLessEqual(jobs[0]['finished_at'],jobs[1]['started_at'])
        self.assertEqual(result['closedError']['code'],'RESOURCE_CLOSED')
        self.assertEqual(result['traceAfterFailure'],[])
        self.assertNotEqual(result['traceAfterCallerMutation'][0]['processor'],'V_MUTATION')

    def test_actual_active_close_external_worker_crash_and_startup_deadline_reap(self):
        result=asyncio.run(active_close_crash_timeout_probe(self.ELK,self.request))
        self.assertEqual(result['close']['error']['code'],'RESOURCE_CLOSED')
        self.assertEqual(result['externalCrash']['error']['type'],'WorkerExecutionError')
        self.assertEqual(result['timeout']['error']['code'],'EXECUTION_TIMEOUT')

    def test_actual_multi_instance_overlap_active_loop_rejection_and_idle_rebinding(self):
        result=asyncio.run(overlap_loop_probe(self.ELK,self.request))
        self.assertNotEqual(result['overlap']['osPids'][0]['pid'],result['overlap']['osPids'][1]['pid'])
        self.assertEqual(result['crossLoop']['error']['code'],'EVENT_LOOP_CONFLICT')


if __name__=='__main__':unittest.main()
