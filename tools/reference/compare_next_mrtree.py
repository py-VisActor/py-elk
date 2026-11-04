"""Run a selected private provider, with its actual generic-micro behavior.

Saved official requests/observations are read only by this development tool.
No installed-package, complete parser or recursive-engine acceptance is made.
"""
from pathlib import Path
import argparse
import base64
import copy
import hashlib
import json
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]


def digest(raw): return hashlib.sha256(raw).hexdigest()


def source_tree(source):
    return {p.relative_to(source).as_posix():digest(p.read_bytes())
            for p in sorted((source/'pyelk').rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def generated_hash_paths(node,path=''):
    paths=set()
    if '$H' not in node: paths.add(path+'/$H')
    for index,port in enumerate(node.get('ports',[])):
        if '$H' not in port: paths.add(path+'/ports/'+str(index)+'/$H')
    for index,child in enumerate(node.get('children',[])):
        paths.update(generated_hash_paths(child,path+'/children/'+str(index)))
    return paths


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--oracle',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--case')
    parser.add_argument('--provider',choices=('fixed','box','random','mrtree'),default='mrtree',
                        help='Radial uses compare_radial.py with separate wire/finite-geometry results')
    args=parser.parse_args()
    if args.out.exists(): raise FileExistsError('Preserve old report; use a new output path')
    source=args.source.resolve();before=source_tree(source)
    sys.path.insert(0,str(source));sys.path.insert(0,str(ROOT/'scripts'))
    import pyelk
    from pyelk.execution.json_transfer import JsonLayoutSession
    from importlib import import_module
    provider=import_module('pyelk.algorithms.'+args.provider)
    from layout_checks import diff
    if Path(pyelk.__file__).resolve()!=source/'pyelk/__init__.py': raise ValueError('Wrong private import root')
    oracle_raw=args.oracle.read_bytes();oracle=json.loads(oracle_raw)
    assert oracle['upstream']['distributionSha256']['lib/elk-worker.js']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    rows=[]
    for entry in oracle['cases']:
        if args.case and entry['id']!=args.case: continue
        request_raw=base64.b64decode(entry['requestBytesBase64'],validate=True)
        observation_raw=base64.b64decode(entry['observationBytesBase64'],validate=True)
        assert digest(request_raw)==entry['requestSha256'] and digest(observation_raw)==entry['observationSha256']
        request=json.loads(request_raw);original=json.loads(observation_raw)
        assert original['requestSha256']==digest(request_raw) and original['outcome']=='returned'
        saved=copy.deepcopy(request);hooks=[]
        row={'id':entry['id'],'originalRequestSha256':digest(request_raw),'originalObservationSha256':digest(observation_raw)}
        try:
            constructor=request.get('constructor',{});arguments=request.get('layoutArguments',{})
            selected=arguments.get('layoutOptions',constructor.get('defaultLayoutOptions',{}))
            session=JsonLayoutSession(request['graph'],selected)
            real_micro=session.node_micro_layout
            def observe(node):
                hooks.append(id(node));return real_micro(node)
            session.node_micro_layout=observe
            provider._layout(session,session.graph)
            result=session.export()
            strict=diff(original['result'],result,tolerant=False)
            numeric=diff({'result':original['result']},{'result':result},tolerant=True)
            hashes={'/result'+p for p in generated_hash_paths(request['graph'])}
            def is_runtime_hash(item):
                return item['path'] in hashes and item['kind']=='missing' and type(item.get('expected')) is int
            mandatory=[d for d in numeric['differences'] if not is_runtime_hash(d)]
            row.update(result=result,strictDifference=strict,geometryBusinessDifference=numeric,
                       mandatoryDifferences=mandatory,observedDefaultMicroCalls=len(hooks),
                       inputPreserved=diff(saved,request,tolerant=False)['passed'],
                       passed=not mandatory and len(hooks)==(1 if args.provider=='mrtree' else 0) and saved==request)
        except Exception as error:
            row.update(passed=False,errorType=type(error).__name__,error=str(error),
                       traceback=traceback.format_exc(),observedDefaultMicroCalls=len(hooks))
        rows.append(row)
    assert rows and (not args.case or len(rows)==1),'Requested case was not found'
    assert source_tree(source)==before,'Private source changed during this run'
    report={'passed':all(r['passed'] for r in rows),'caseCount':len(rows),'rows':rows,
            'sourceTreeSha256':before,'importedModulePath':str(Path(provider.__file__).resolve()),'provider':args.provider,
            'comparatorSha256':digest(Path(__file__).read_bytes()),'comparisonHelperSha256':digest((ROOT/'scripts/layout_checks.py').read_bytes()),
            'originalOracleSha256':digest(oracle_raw),'fullValidation':False,'referenceReexecuted':False,
            'installedPackageValidated':False,'publicAPIIntegrated':False,'wholeAlgorithmAccepted':False,
            'scope':'Actual private one-provider call with default generic NodeMicroLayout; full raw strict differences retained; existing numeric tolerances only; no arbitrary input cap'}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as handle: json.dump(report,handle,indent=2,allow_nan=False)
    print(json.dumps({'passed':report['passed'],'caseCount':len(rows),
                     'failedCases':[r['id'] for r in rows if not r['passed']],
                     'mandatoryDifferenceCount':sum(len(r.get('mandatoryDifferences',[])) for r in rows),
                     'observedDefaultMicroCalls':sum(r['observedDefaultMicroCalls'] for r in rows)}))
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
