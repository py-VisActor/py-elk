"""PRIVATE_SRC REQUEST ORACLE REPORT: new PG01/04 foundation objects.

All raw error records remain. Only the declared Java bounds -> Python IndexError
family mapping is used for semantic parity; raw error text parity is separate.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={p.resolve():sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0,str(source))
    from pyelk.algorithms.polyomino import PlanarGrid
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    original=json.loads(oracle.read_bytes());assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('polyomino-grid-probe.cjs'))
    def attempt(call):
        try:return dict(outcome='returned',value=call())
        except Exception as error:return dict(outcome='threw',error=dict(name=type(error).__name__,message=str(error),text=type(error).__name__+': '+str(error)))
    def semantic(value):
        if type(value) is dict:
            if value.get('outcome')=='threw' and 'error' in value:
                error=value['error'];family=error['name']
                if family=='Error' and error['message'].startswith('java.lang.IndexOutOfBoundsException:'):family='IndexError'
                return dict(outcome='threw',errorFamily=family)
            return {k:semantic(v) for k,v in value.items()}
        if type(value) is list:return list(map(semantic,value))
        return value
    rows=[]
    for case,expected in zip(json.loads(request.read_bytes())['cases'],original['results'],strict=True):
        assert case['id']==expected['id'];grid=PlanarGrid(*case['size'])
        def snapshot():return dict(size=[grid.x_size,grid.y_size],center=[grid.x_center,grid.y_center],wordCounts=[len(row) for row in grid.grid],cells=[[grid.retrieve(x,y) for x in range(grid.x_size)] for y in range(grid.y_size)],text=str(grid))
        if case['operation']=='words':
            for args in case['sets']:grid.set(*args)
            flags=[dict(x=x,y=y,empty=grid.is_empty(x,y),blocked=grid.is_blocked(x,y),weak=grid.is_weakly_blocked(x,y)) for x,y,*_ in case['sets']]
            value=dict(snapshot=snapshot(),flags=flags,reads=[dict(x=x,y=y,result=attempt(lambda x=x,y=y:grid.retrieve(x,y))) for x,y in case['reads']],
                       badSets=[dict(x=args[0],y=args[1],result=attempt(lambda args=args:grid.set(*args))) for args in case['badSets']],layoutExecuted=False)
        else:
            grid.set_blocked_center_based(0,0);grid.set_weakly_blocked_center_based(-2,-1);grid.weakly_block_area(*case['weakArea'])
            initial=snapshot();weak=grid.weakly_intersects_area(0,0,1,0);all_area=grid.weakly_intersects_area(*case['weakArea'])
            flags=dict(blocked=grid.is_blocked_center_based(0,0),weak=grid.is_weakly_blocked_center_based(-2,-1),empty=grid.is_empty_center_based(1,0))
            old_grid=grid.grid;grid.reinitialize(*case['reinitialize'])
            value=dict(before=initial,weakOnlyAreaIntersects=weak,allAreaIntersects=all_area,centerFlags=flags,after=snapshot(),storageReplaced=grid.grid is not old_grid,layoutExecuted=False)
        raw=diff(expected['value'],value);projected=diff(semantic(expected['value']),semantic(value))
        rows.append(dict(id=case['id'],actual=value,expected=expected['value'],strictRawDifference=raw,valueAndErrorFamilyDifference=projected))
    imported={Path(m.__file__).resolve() for name,m in tuple(sys.modules.items()) if (name=='pyelk' or name.startswith('pyelk.')) and getattr(m,'__file__',None)}
    unchanged=all(sha(p)==before[p] for p in imported)
    parity=unchanged and all(row['valueAndErrorFamilyDifference']['passed'] for row in rows)
    result=dict(valueAndErrorFamilyParity=parity,strictRawParity=all(row['strictRawDifference']['passed'] for row in rows),rows=rows,
                errorPolicy='Raw messages remain in full strict differences. Only source Java IndexOutOfBoundsException maps to native IndexError; native TypeError must match source TypeError. No exact error-text parity is claimed.',
                sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},layoutExecuted=False,
                scope='Source two-bit/center/weak-area object semantics only, with explicit native error-family projection; no raster/packing or public error protocol')
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(valueAndErrorFamilyParity=parity,strictRawParity=result['strictRawParity'],cases=len(rows))))
    return 0 if parity else 1


if __name__=='__main__':raise SystemExit(main())
