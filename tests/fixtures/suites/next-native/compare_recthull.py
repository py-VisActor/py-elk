"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; fresh RectHull, no full layout."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.rectilinear_hull import Point,RectilinearConvexHull
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_bytes());original=json.loads(original_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path)
assert original['probeSha256']==sha(Path(__file__).with_name('recthull-probe.cjs'))
assert original['actualRectHull'] is True and original['layoutExecuted'] is False
def number(v):return 'NaN' if math.isnan(v) else ('Infinity' if v>0 else '-Infinity') if not math.isfinite(v) else '-0' if v==0 and math.copysign(1,v)<0 else v
def coord(p):return list(map(number,(p.x,p.y)))
actual=[];errors=[]
for c in request['cases']:
    points=[Point(*p)for p in c['points']];references=list(points);initial=[coord(p)for p in points];phase='of'
    try:
        hull=RectilinearConvexHull.of(points);phase='split';hull_refs=list(hull.hull);rectangles=hull.split_into_rectangles()
        actual.append({'name':c['name'],'failedPhase':None,'extrema':[points.index(p)if p is not None else -1 for p in (hull.x_max1,hull.x_min1,hull.x_min2,hull.y_max1,hull.y_min1)],
            'hull':[{'point':coord(p),'quadrant':p.quadrant,'convex':p.convex,'inputReference':any(p is v for v in points)}for p in hull.hull],
            'rectangles':[list(map(number,(r.x,r.y,r.width,r.height)))for r in rectangles],
            'inputUnchanged':initial==[coord(p)for p in points] and all(a is b for a,b in zip(references,points)),
            'hullReferencesUnchanged':all(a is b for a,b in zip(hull_refs,hull.hull))})
    except (IndexError,AttributeError) as error:
        errors.append({'name':c['name'],'phase':phase,'type':type(error).__name__,'error':str(error)})
        actual.append({'name':c['name'],'failedPhase':phase})
comparison=diff(original['value'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'rawNativeErrors':errors,
    'exceptionComparisonScope':'Failure phase only; raw original/native exception identities and messages retained separately, no claim of equal runtime exception classes.',
    'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
    'actualRectHull':True,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
