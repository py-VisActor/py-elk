"""Independent OS CPU observations for genuine native worker jobs.

These are test tools, not layout instrumentation. No process-time value is
invented in a product progress event and no synthetic work is called layout.
"""
import asyncio
import ctypes
import os
from pathlib import Path
import time


def process_cpu_seconds(pid):
    if os.name=='nt':
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
        kernel.GetProcessTimes.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        created,exited,kernel_time,user_time=(wintypes.FILETIME()for _ in range(4))
        try:
            if not kernel.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(exited),
                                          ctypes.byref(kernel_time),ctypes.byref(user_time)):
                raise ctypes.WinError(ctypes.get_last_error())
            ticks=sum((value.dwHighDateTime<<32)|value.dwLowDateTime for value in(kernel_time,user_time))
            return ticks*1e-7
        finally:kernel.CloseHandle(handle)
    # Linux stat comm may contain spaces and parentheses. The suffix starts
    # at field3, so utime/stime (fields14/15) are suffix offsets11/12.
    text=(Path('/proc')/str(pid)/'stat').read_text(encoding='utf-8')
    fields=text[text.rfind(')')+2:].split()
    return(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')


def cpu_graph(iterations=400,nodes=40):
    return {'id':'native-real-cpu','layoutOptions':{'algorithm':'force','randomSeed':42,
                                                  'force.iterations':iterations},
            'children':[{'id':str(i),'width':20,'height':15}for i in range(nodes)],
            'edges':[{'id':'e'+str(i),'sources':[str(i)],'targets':[str(i+1)]}for i in range(nodes-1)]}


async def wait_for_cpu(instance,task,minimum_seconds=.02,timeout=15):
    started=time.monotonic();observations=[];heartbeats=[]
    while time.monotonic()-started<timeout:
        if task.done():
            await task
            raise AssertionError('Native job returned before the OS CPU observation interval')
        snapshot=instance._controller.snapshot()
        jobs=[job for job in snapshot['jobs']if job['state']=='running'and job['progress']is not None]
        if jobs and snapshot['worker_alive']:
            sample={'observedAt':time.monotonic(),'snapshot':snapshot,
                    'cpuSeconds':process_cpu_seconds(jobs[-1]['pid'])}
            if not observations:observations.append(sample)
            heartbeats.append(sample['observedAt'])
            if sample['cpuSeconds']-observations[0]['cpuSeconds']>=minimum_seconds:
                observations.append(sample)
                return {'observations':observations,'snapshots':[x['snapshot']for x in observations],
                        'cpuSeconds':[x['cpuSeconds']for x in observations],'heartbeats':heartbeats}
        await asyncio.sleep(.001)
    raise AssertionError('No positive real worker OS CPU interval observed')
