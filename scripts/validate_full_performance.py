"""Measure the installed full candidate, without certifying an older wheel.

Plan mode is pure. Execution installs the supplied artifact outside the repo,
uses an isolated interpreter, and records every warmup/sample and OS counter.
No claim is made for sizes, platforms or algorithm options that were not run.
"""
from __future__ import annotations
import argparse
import asyncio
from collections import deque
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import venv
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ALGORITHMS=('fixed','box','random','layered','mrtree','radial','force','stress',
            'disco','sporeOverlap','sporeCompaction','rectpacking')
SIZES=(8,32,96)


def plan(algorithms=None):
    selected=ALGORITHMS if algorithms is None else tuple(algorithms)
    if not selected or set(selected)-set(ALGORITHMS):raise ValueError('Expected known algorithm names')
    rows=[{'algorithm':algorithm,'nodes':size,'options':{}}
          for algorithm in ALGORITHMS if algorithm in selected for size in SIZES]
    if 'force'in selected:
        rows.extend({'algorithm':'force','nodes':size,'options':{'force.model':'EADES'}}for size in SIZES)
    return {'schema':'py-elk-full-performance-plan/v1','profiles':rows,'warmups':1,'samples':5,
            'seed':37,'jobTimeoutSeconds':60,'memoryObservation':'OS worker peak working set / VmHWM',
            'quality':'Bounding extent, overlaps, edge lengths; connected-tree normalized stress',
            'convergenceLimits':[1,25,150],'convergenceAlgorithms':[x for x in('force','stress')if x in selected],
            'selectedAlgorithms':[x for x in ALGORITHMS if x in selected],'platform':platform.system(),
            'fullValidation':False,'layoutExecutions':0}


def graph_for(algorithm,size,options=None):
    columns=math.ceil(math.sqrt(size));overlap=algorithm in('sporeOverlap','sporeCompaction','disco')
    children=[{'id':str(i),'width':24,'height':16,
               'x':(i%columns)*(12 if overlap else 70)+(i*17%11)*.1,
               'y':(i//columns)*(9 if overlap else 55)+(i*13%7)*.1}for i in range(size)]
    edges=[]
    if algorithm in('layered','mrtree','radial','force','stress'):
        edges=[{'id':'e'+str(i),'sources':[str((i-1)//2)],'targets':[str(i)]}for i in range(1,size)]
    elif algorithm=='disco':
        edges=[{'id':'e'+str(i),'sources':[str(i-1)],'targets':[str(i)]}
               for i in range(1,size)if i%3]
    return {'id':'performance','layoutOptions':{'algorithm':algorithm,'randomSeed':37,**(options or{})},
            'children':children,'edges':edges}


def quality(graph,*,desired_length=100):
    nodes=graph['children'];by_id={node['id']:node for node in nodes}
    def center(node):return(node['x']+node['width']/2,node['y']+node['height']/2)
    centers={key:center(node)for key,node in by_id.items()}
    overlaps=0
    for i,first in enumerate(nodes):
        for second in nodes[i+1:]:
            if(min(first['x']+first['width'],second['x']+second['width'])>max(first['x'],second['x'])
               and min(first['y']+first['height'],second['y']+second['height'])>max(first['y'],second['y'])):
                overlaps+=1
    lengths=[];adjacency={key:[]for key in by_id}
    for edge in graph.get('edges',[]):
        a,b=edge['sources'][0],edge['targets'][0]
        lengths.append(math.dist(centers[a],centers[b]));adjacency[a].append(b);adjacency[b].append(a)
    numerator=denominator=0.;pairs=0
    keys=list(by_id)
    for i,start in enumerate(keys):
        distance={start:0};pending=deque([start])
        while pending:
            current=pending.popleft()
            for other in adjacency[current]:
                if other not in distance:distance[other]=distance[current]+1;pending.append(other)
        for target in keys[i+1:]:
            if target in distance:
                expected=distance[target]*desired_length
                numerator+=(math.dist(centers[start],centers[target])-expected)**2
                denominator+=expected**2;pairs+=1
    return {'overlappingNodePairs':overlaps,'meanEdgeLength':statistics.mean(lengths)if lengths else None,
            'maxEdgeLength':max(lengths)if lengths else None,
            'normalizedGraphStress':numerator/denominator if denominator else None,
            'stressConnectedPairs':pairs}


def process_counters(pid):
    if os.name=='nt':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
                (name,ctypes.c_size_t)for name in('PeakWorkingSetSize','WorkingSetSize',
                'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
        kernel.GetProcessTimes.restype=wintypes.BOOL
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
        handle=kernel.OpenProcess(0x0410,False,pid)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        try:
            created,exited,system,user=(wintypes.FILETIME()for _ in range(4))
            if not kernel.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(exited),ctypes.byref(system),ctypes.byref(user)):
                raise ctypes.WinError(ctypes.get_last_error())
            memory=Counters();memory.cb=ctypes.sizeof(memory)
            if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(memory),memory.cb):
                raise ctypes.WinError(ctypes.get_last_error())
            return {'method':'GetProcessTimes/GetProcessMemoryInfo','pid':pid,
                    'cpuSeconds':sum((x.dwHighDateTime<<32)|x.dwLowDateTime for x in(system,user))*1e-7,
                    'workingSetBytes':memory.WorkingSetSize,'peakWorkingSetBytes':memory.PeakWorkingSetSize}
        finally:kernel.CloseHandle(handle)
    fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
    status={line.split(':',1)[0]:line.split(':',1)[1].strip()for line in(Path('/proc')/str(pid)/'status').read_text().splitlines()if':'in line}
    return {'method':'Linux /proc stat/status','pid':pid,
            'cpuSeconds':(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK'),
            'workingSetBytes':int(status['VmRSS'].split()[0])*1024,
            'peakWorkingSetBytes':int(status['VmHWM'].split()[0])*1024}


def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


async def capture(args):
    import pyelk
    assert sys.flags.isolated and Path(pyelk.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    with zipfile.ZipFile(args.wheel)as archive:
        expected={name:hashlib.sha256(archive.read(name)).hexdigest()for name in archive.namelist()if name.startswith('pyelk/')}
    package=Path(pyelk.__file__).parent
    actual={'pyelk/'+p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in package.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
    assert expected==actual,'Installed payload differs from measured artifact'
    rows=[]
    measurement_plan=plan(args.algorithm)
    for profile in measurement_plan['profiles']:
        row={**profile,'samples':[]};request=graph_for(profile['algorithm'],profile['nodes'],profile['options'])
        before=fingerprint(request)
        try:
            with pyelk.ELK(timeout=60)as elk:
                start=time.perf_counter();warm=await elk.layout(request)
                pid=elk._controller.snapshot()['worker_pid']
                row['warmup']={'wallSeconds':time.perf_counter()-start,'worker':process_counters(pid)}
                for sample in range(5):
                    counter_before=process_counters(pid);start=time.perf_counter()
                    result=await elk.layout(request)
                    elapsed=time.perf_counter()-start;counter_after=process_counters(pid)
                    assert len(result['children'])==profile['nodes']
                    assert all(type(node[k])in(int,float)and math.isfinite(node[k])
                               for node in result['children']for k in('x','y','width','height'))
                    assert fingerprint(request)==before,'Caller input was mutated'
                    row['samples'].append({'index':sample,'wallSeconds':elapsed,
                        'workerCpuSeconds':counter_after['cpuSeconds']-counter_before['cpuSeconds'],
                        'worker':counter_after,'resultSha256':fingerprint(result)})
                row['quality']=quality(result)
                row['workerReused']=all(sample['worker']['pid']==pid for sample in row['samples'])
                row['passed']=row['workerReused']
            times=[x['wallSeconds']for x in row['samples']]
            row['statistics']={'medianWallSeconds':statistics.median(times),'maxWallSeconds':max(times),
                'p95NearestRankWallSeconds':sorted(times)[math.ceil(.95*len(times))-1],
                'maxWorkerPeakBytes':max(x['worker']['peakWorkingSetBytes']for x in row['samples'])}
        except Exception as error:
            row.update(passed=False,error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())
        rows.append(row);save(args.out/'profiles.json',rows)
        print(json.dumps({'algorithm':profile['algorithm'],'nodes':profile['nodes'],'options':profile['options'],
                          'passed':row['passed'],'statistics':row.get('statistics'),'error':row.get('error')}),flush=True)
    convergence=[]
    for algorithm in measurement_plan['convergenceAlgorithms']:
        for limit in(1,25,150):
            options={('force.iterations'if algorithm=='force'else'stress.iterationLimit'):limit}
            if algorithm=='stress':options['stress.epsilon']=0
            request=graph_for(algorithm,32,options);row={'algorithm':algorithm,'limit':limit,'options':options}
            try:
                with pyelk.ELK(timeout=60)as elk:
                    start=time.perf_counter();result=await elk.layout(request)
                    row.update(passed=True,wallSeconds=time.perf_counter()-start,quality=quality(result),
                               resultSha256=fingerprint(result),worker=process_counters(elk._controller.snapshot()['worker_pid']))
            except Exception as error:row.update(passed=False,error=str(error))
            convergence.append(row)
    save(args.out/'convergence.json',convergence)
    report={'schema':'py-elk-installed-full-performance/v1','passed':all(x['passed']for x in rows+convergence),
            'version':pyelk.__version__,'python':sys.version,'executable':sys.executable,
            'platform':platform.platform(),'package':str(package),'isolated':True,'runtimeFilesSha256':actual,
            'wheelSha256':hashlib.sha256(args.wheel.read_bytes()).hexdigest(),'plan':measurement_plan,'profiles':rows,
            'convergenceObservations':convergence,'claimedUniversalResourceLimit':None,
            'scope':'This artifact/interpreter/host, declared finite inputs and options only; warmups separated from steady-state samples'}
    save(args.out/'report.json',report)
    return 0 if report['passed']else 1


def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-only',action='store_true');parser.add_argument('--capture',action='store_true')
    parser.add_argument('--wheel',type=Path);parser.add_argument('--out',type=Path)
    parser.add_argument('--algorithm',action='append',choices=ALGORITHMS,
                        help='Measure only the named affected algorithm; repeat to select more')
    args=parser.parse_args()
    if args.plan_only:print(json.dumps(plan(args.algorithm),indent=2));return 0
    if args.wheel is None or args.out is None:parser.error('--wheel and --out are required for measurement')
    args.wheel=args.wheel.resolve();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    if args.capture:return asyncio.run(capture(args))
    with tempfile.TemporaryDirectory(prefix='pyelk-full-performance-')as temp:
        folder=Path(temp);environment=folder/'venv';venv.EnvBuilder(with_pip=True).create(environment)
        python=environment/('Scripts/python.exe'if os.name=='nt'else'bin/python')
        commands=[('install',[str(python),'-I','-m','pip','install','--no-index','--no-deps',str(args.wheel)]),
                  ('capture',[str(python),'-I',str(Path(__file__).resolve()),'--capture','--wheel',str(args.wheel),
                              '--out',str(args.out/'installed'),
                              *[part for name in(args.algorithm or[])for part in('--algorithm',name)]])]
        records=[]
        for name,command in commands:
            start=time.perf_counter();process=subprocess.run(command,cwd=folder,capture_output=True,timeout=900)
            (args.out/(name+'.stdout.log')).write_bytes(process.stdout);(args.out/(name+'.stderr.log')).write_bytes(process.stderr)
            records.append({'name':name,'argv':command,'exitCode':process.returncode,'seconds':time.perf_counter()-start})
            save(args.out/'commands.json',records)
            if process.returncode:
                print(process.stderr.decode(errors='replace')[-3000:]);return process.returncode
    print('Installed full performance measurement complete: '+str(args.out/'installed/report.json'))
    return 0


if __name__=='__main__':raise SystemExit(main())
