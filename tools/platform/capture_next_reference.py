"""Small original-only migration probes through the existing single-request oracle.

Every request starts a real independent Node process. No Python product or
candidate output is imported; these facts do not mark E13/E16 complete.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
COLLECTOR='tools/reference/capture_layout.cjs'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):
    with Path(path).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def encoded(raw):return base64.b64encode(raw).decode()


def command(argv,folder,environment):
    folder.mkdir();started=time.perf_counter()
    process=subprocess.Popen(argv,cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    timed_out=False
    try:stdout,stderr=process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        timed_out=True;process.kill();stdout,stderr=process.communicate()
    (folder/'stdout.log').write_bytes(stdout);(folder/'stderr.log').write_bytes(stderr)
    record={'argv':list(map(str,argv)),'cwd':str(ROOT),'pid':process.pid,'exitCode':process.returncode,
            'timedOut':timed_out,'elapsedSeconds':time.perf_counter()-started,
            'stdoutSha256':digest(stdout),'stderrSha256':digest(stderr),
            'environmentPolicy':{'nodeOverridesAbsent':not any(k.upper() in ('NODE_OPTIONS','NODE_PATH') for k in environment)}}
    save(folder/'command.json',record)
    return {'command':record,'stdoutBytesBase64':encoded(stdout),'stderrBytesBase64':encoded(stderr)}


def capture(node,package,suite,out):
    out.mkdir(parents=True,exist_ok=False)
    lock=json.loads((ROOT/'UPSTREAM.json').read_bytes());definitions=json.loads((suite/'cases.json').read_bytes())
    environment={k:v for k,v in os.environ.items() if k.upper() not in ('NODE_OPTIONS','NODE_PATH')}
    upstream={'version':lock['javascript']['version'],'commit':lock['javascript']['commit'],
              'distributionSha256':lock['distribution']['sha256Files']}
    def package_hashes():
        return {name:digest((package/name).read_bytes()) for name in upstream['distributionSha256']}
    before=package_hashes()
    if before!=upstream['distributionSha256']:raise ValueError('Original npm package bytes differ')
    collector=ROOT/COLLECTOR;collector_sha=digest(collector.read_bytes())
    node_sha=digest(node.read_bytes())
    identity=command([str(node),'--version'],out/'node-version',environment)
    if identity['command']['exitCode']!=0:raise ValueError('Actual Node identity command failed')
    rows=[]
    for definition in definitions['cases']:
        original=suite/definition['request'];raw=original.read_bytes();request=json.loads(raw)
        folder=out/definition['id'];folder.mkdir();request_path=folder/'request.json';request_path.write_bytes(raw)
        observation=folder/'observation.json'
        receipt=command([str(node),str(collector),str(package),str(request_path),str(observation)],folder/'execution',environment)
        if receipt['command']['exitCode']!=0 or receipt['command']['timedOut']:
            raise ValueError('Reference process failed; original command/logs retained')
        observed=observation.read_bytes();value=json.loads(observed)
        if value['requestSha256']!=digest(raw) or original.read_bytes()!=raw:
            raise ValueError('Original request bytes changed')
        rows.append({'id':definition['id'],'definition':definition,'requestBytesBase64':encoded(raw),
                     'requestSha256':digest(raw),'request':request,**receipt,
                     'observationBytesBase64':encoded(observed),'observationSha256':digest(observed)})
    if package_hashes()!=before or digest(collector.read_bytes())!=collector_sha or digest(node.read_bytes())!=node_sha:
        raise ValueError('Original engine/collector identity changed during probes')
    record={'schema':'py-elk-next-native-reference/v1','actualSourceRoot':str(ROOT),
            'scope':'Independent original-only probes for planned E13/E16 migration; no candidate or completed algorithm acceptance.',
            'upstream':upstream,'collector':COLLECTOR,'collectorSha256':collector_sha,
            'captureDriverSha256':digest(Path(__file__).read_bytes()),
            'node':str(node),'nodeSha256':node_sha,'nodeIdentityCommand':identity,
            'suiteSha256':digest((suite/'cases.json').read_bytes()),'cases':rows,
            'actualReferenceProcesses':len(rows),'candidateExecuted':False,'iterationsCompleted':[],
            'fullValidation':False,'historicalExecutionAuthenticated':False}
    save(out/'receipt.json',record);return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node',required=True,type=Path);parser.add_argument('--package',required=True,type=Path)
    parser.add_argument('--suite',type=Path,default=ROOT/'tests/fixtures/suites/next-native')
    parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    result=capture(args.node.resolve(),args.package.resolve(),args.suite.resolve(),args.out.resolve())
    print(json.dumps({'cases':len(result['cases']),'actualReferenceProcesses':result['actualReferenceProcesses'],
                      'candidateExecuted':False,'fullValidation':False}))


if __name__=='__main__':main()
