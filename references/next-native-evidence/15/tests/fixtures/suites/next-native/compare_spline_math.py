from pathlib import Path
import sys,json,hashlib
source,request,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.graph import Vec2
from pyelk.algorithms.layered.spline_math import NubSpline
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
vec=lambda p:[p.x,p.y];before=hashes();actual=[]
for points in json.loads(request.read_text(encoding='utf8'))['primitivePoints']:
 chain=[Vec2(*p)for p in points];prior=chain.copy();spline=NubSpline(chain);cp=spline.get_bezier_control_points();same=spline.get_bezier_control_points()
 actual.append({'inputSize':len(points),'mutatedChain':[vec(p)for p in chain],'firstReferenceRetained':chain[0]is prior[0],'knots':spline.knot_vector,'controls':[{'cp':vec(p.cp),'polar':p.polar_coordinate}for p in spline.control_points],'bezier':[vec(p)for p in cp],'repeatSameReferences':all(p is same[i]for i,p in enumerate(cp)),'isBezier':spline.is_bezier,'isClamped':spline.is_clamped})
expected=json.loads(original.read_text(encoding='utf8'))['value']['primitives'];comparison=diff(expected,actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':expected,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'Only new actual NubSpline three prepared object controls (2/4/7 initial points); exact knots, controls, polar lists, mutated input-chain reference, internal Bezier CP references stable on repeat. Original router/misread monitor fields not consumed; no layout/backend/general spline phase claim.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
