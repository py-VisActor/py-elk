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
from layout_checks import diff, _project_reference_shape_hashes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--original',required=True,type=Path)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--project-reference-shape-hashes',action='store_true')
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    request=json.loads(args.request.read_bytes());original=json.loads(args.original.read_bytes())
    candidate=json.loads(args.candidate.read_bytes())
    if original['outcome']!='returned' or original['requestSha256']!=sha(args.request):
        raise ValueError('Expected a returned reference observation bound to this request')
    raw=diff(original['result'],candidate,tolerant=False)
    projected=copy.deepcopy(original['result']);adaptations=[];violations=[]
    if args.project_reference_shape_hashes:
        _project_reference_shape_hashes(request['graph'],projected,candidate,prefix='/result',
                                        adaptations=adaptations,violations=violations)
    comparison=diff(projected,candidate,tolerant=False)
    report={'passed':comparison['passed']and not violations,'rawStrict':raw,
      'comparison':comparison,'adaptations':adaptations,'violations':violations,
      'projectionOptedIn':args.project_reference_shape_hashes,
      'validationScope':'saved-json-result-delta-only','runtimeExecutions':0,
      'nativeExecutionVerified':False,'inputPreservationVerified':False,
      'wholeAlgorithmAccepted':False,'fullValidation':False,
      'filesSha256':{str(p):sha(p)for p in(args.request,args.original,args.candidate,Path(__file__))}}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf8',newline='\n')as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({k:report[k]for k in('passed','projectionOptedIn','runtimeExecutions')}))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
