"""Recompare saved new Layered results, preserving raw diffs; no products.

This verifies JSON comparison only. It does not certify an execution, a source
tree, package installation, or the complete algorithm. Runtime receipts and
immutable source manifests remain separate evidence.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import layout_checks
from layout_checks import diff, _project_reference_shape_hashes


def project_hierarchy_shape_hashes(original, reference, candidate, *, adaptations, violations):
    """Apply the existing node rule in explicitly verified child graph contexts.

    Preflight every node identity/child array before mutating the reference
    copy. Business mappings, edges, ports and labels are never traversed.
    This is a separate opt-in scope, not a change to the flat v1 profile.
    """
    contexts=[];pending=[(original,reference,candidate,'/result')]
    while pending:
        before,after,native,path=pending.pop()
        if not all(isinstance(value,dict) for value in(before,after,native)):
            violations.append({'path':path,'reason':'Hierarchy shape mappings differ'})
            continue
        if any(not diff(before.get('id'),value.get('id'),tolerant=False)['passed'] for value in(after,native)):
            violations.append({'path':path,'reason':'Hierarchy node identity differs'})
            continue
        children=[value.get('children',[]) for value in(before,after,native)]
        if not all(isinstance(value,list)for value in children) or len({len(value)for value in children})!=1:
            violations.append({'path':path+'/children','reason':'Hierarchy child arrays or counts differ'})
            continue
        if children[0] or path=='/result':
            contexts.append((before,after,native,path))
        for index in range(len(children[0])-1,-1,-1):
            pending.append((*[value[index]for value in children],path+f'/children/{index}'))
    if violations:
        return 0
    for before,after,native,path in contexts:
        _project_reference_shape_hashes(before,after,native,prefix=path,
                                        adaptations=adaptations,violations=violations)
    for item in adaptations:
        item['contextRule']='GWT-SHAPE-HASH-HIERARCHY-01'
    return len(contexts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--original',required=True,type=Path)
    parser.add_argument('--candidate',required=True,type=Path)
    projection=parser.add_mutually_exclusive_group()
    projection.add_argument('--project-reference-shape-hashes',action='store_true')
    projection.add_argument('--project-reference-hierarchy-shape-hashes',action='store_true')
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    request=json.loads(args.request.read_bytes());original=json.loads(args.original.read_bytes())
    candidate=json.loads(args.candidate.read_bytes())
    if original['outcome']!='returned' or original['requestSha256']!=sha(args.request):
        raise ValueError('Expected a returned reference observation bound to this request')
    lock_path=Path(__file__).resolve().parents[2]/'UPSTREAM.json'
    lock=json.loads(lock_path.read_bytes());engine=original.get('engine',{})
    if (original.get('schema')!='py-elk-layout-observation/v1' or engine.get('name')!='elkjs'
            or engine.get('version')!=lock['javascript']['version']
            or engine.get('entrypoint')!='lib/elk.bundled.js'
            or engine.get('entrypointSha256')!=lock['distribution']['sha256Files']['lib/elk.bundled.js']):
        raise ValueError('Expected the locked stock reference observation identity')
    raw=diff(original['result'],candidate,tolerant=False)
    projected=copy.deepcopy(original['result']);adaptations=[];violations=[]
    if args.project_reference_shape_hashes:
        _project_reference_shape_hashes(request['graph'],projected,candidate,prefix='/result',
                                        adaptations=adaptations,violations=violations)
    contexts=0
    if args.project_reference_hierarchy_shape_hashes:
        contexts=project_hierarchy_shape_hashes(request['graph'],projected,candidate,
                                                adaptations=adaptations,violations=violations)
    comparison=diff(projected,candidate,tolerant=False)
    report={'passed':comparison['passed']and not violations,'rawStrict':raw,
      'comparison':comparison,'adaptations':adaptations,'violations':violations,
      'projectionOptedIn':args.project_reference_shape_hashes or args.project_reference_hierarchy_shape_hashes,
      'hierarchyProjectionOptedIn':args.project_reference_hierarchy_shape_hashes,
      'hierarchyContextsVisited':contexts,'stockReferenceIdentityChecked':True,
      'validationScope':'saved-json-result-delta-only','runtimeExecutions':0,
      'nativeExecutionVerified':False,'inputPreservationVerified':False,
      'wholeAlgorithmAccepted':False,'fullValidation':False,
      'filesSha256':{str(p):sha(p)for p in(args.request,args.original,args.candidate,Path(__file__),Path(layout_checks.__file__),lock_path)}}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf8',newline='\n')as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({k:report[k]for k in('passed','projectionOptedIn','runtimeExecutions')}))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
