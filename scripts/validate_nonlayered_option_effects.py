"""Causal non-Layered public API contrasts; fixed Source captured once.

Reuses the shared effect schema and comparator. Geometry pointers are selected
from Source baseline/variant differences only, before reading any candidate.
Unchanged Source outputs remain failed attempts, not inferred option effects.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from layout_checks import diff,load,_GEOMETRY
from validate_option_effects import definitions,compare
from validate_full_layered import command_capture,sha,write

SUITE=ROOT/'tests/fixtures/suites/full-option-effects-nonlayered/cases.json'


def source_proofs(rows,reference):
    originals={case['id']:load(reference/(case['id']+'.json'))for case,_ in rows}
    selected=[];result=[]
    for case,request in rows:
        case=copy.deepcopy(case)
        if case.get('baseline'):
            before=originals[case['baseline']];after=originals[case['id']]
            pointers=[]
            if before['outcome']==after['outcome']=='returned':
                changes=diff({'result':before['result']},{'result':after['result']},tolerant=True)
                pointers=[d['path']for d in changes['differences']if d['kind']=='number'and _GEOMETRY.fullmatch(d['path'])]
            # Preserve a real no-effect attempt when Source did not change.
            if not pointers:pointers=['/result/width','/result/height']
            for proof in case['proofs']:proof['pointers']=pointers
            selected.append({'id':case['id'],'baseline':case['baseline'],'pointers':pointers,
                             'referenceSha256':sha(reference/(case['id']+'.json')),
                             'baselineReferenceSha256':sha(reference/(case['baseline']+'.json'))})
        result.append((case,request))
    return result,selected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,default=SUITE)
    parser.add_argument('--capture',choices=('reference','candidate'))
    parser.add_argument('--reference',type=Path);parser.add_argument('--candidate',type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--node',type=Path,default=Path('C:/Program Files/nodejs/node.exe'))
    parser.add_argument('--exclude',nargs='*',default=[],help='Explicitly omit failed capture rows from this partial comparison; raw failures are retained separately')
    args=parser.parse_args();rows=definitions(args.suite.resolve());out=args.out.resolve()
    if args.capture:
        out.mkdir(parents=True,exist_ok=False)
        (out/'executed-suite.json').write_bytes(args.suite.read_bytes())
        (out/'executed-wrapper.py').write_bytes(Path(__file__).read_bytes())
        if args.capture=='reference':
            batch=out/'batch.json';write(batch,{'cases':[{'id':case['id'],'request':str(request),'output':str(out/(case['id']+'.json'))}for case,request in rows]})
            commands=[command_capture([str(args.node.resolve()),str(ROOT/'tools/reference/full_layered.cjs'),str(ROOT/'.local/npm-elkjs/package'),str(batch)],out/'command',180)]
        else:
            commands=[command_capture([sys.executable,'-I',str(ROOT/'scripts/validate_full_layered.py'),'--capture-candidate',str(request),'--source',str(ROOT/'src'),'--out',str(out/(case['id']+'.json'))],out/(case['id']+'-command'),60)for case,request in rows]
        write(out/'receipt.json',{'schema':'py-elk-nonlayered-option-capture/v1','role':args.capture,'caseCount':len(rows),'suiteSha256':sha(args.suite),'commands':commands,'passed':all(c['exitCode']==0 and not c['timedOut']for c in commands)})
        return 0 if all(c['exitCode']==0 and not c['timedOut']for c in commands)else 1
    if args.reference is None or args.candidate is None:parser.error('Comparison requires both original capture directories')
    unknown=set(args.exclude)-{case['id']for case,_ in rows}
    if unknown:parser.error('Unknown excluded cases: '+str(sorted(unknown)))
    selected_rows=[(case,request)for case,request in rows if case['id']not in args.exclude]
    if any(case.get('baseline')in args.exclude for case,_ in selected_rows):parser.error('An included contrast needs an excluded baseline')
    selected,pointers=source_proofs(selected_rows,args.reference.resolve())
    write(out.with_name(out.stem+'-source-pointers.json'),{'sourceOnlySelection':True,'candidateReadForSelection':False,'rows':pointers})
    if args.exclude:
        write(out.with_name(out.stem+'-excluded-captures.json'),{'allCasesCompared':False,'caseIds':args.exclude,
             'referenceObservations':{name:load(args.reference/(name+'.json'))for name in args.exclude},
             'note':'Excluded capture errors/timeouts are not effect passes or Source/native parity.'})
    return compare(selected,args.reference.resolve(),args.candidate.resolve(),out)


if __name__=='__main__':raise SystemExit(main())
