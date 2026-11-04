"""PRIVATE_SRC ALGORITHM TASK REQUEST SAVED_DIRECT_NATIVE NEW_REPORT."""
import copy,hashlib,json,sys
from pathlib import Path
source=Path(sys.argv[1]);algorithm,task=sys.argv[2:4];request_path,baseline_path,out=map(Path,sys.argv[4:7])
sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from layout_checks import diff
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.diagnostics import BasicProgressMonitor
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));baseline=json.loads(baseline_path.read_text('utf-8'));saved=copy.deepcopy(request)
assert baseline['sourceWireParity']is True and baseline['validFiniteGeometry']is True and not baseline['mandatoryDifferences']
selected=request.get('layoutArguments',{}).get('layoutOptions',request.get('constructor',{}).get('defaultLayoutOptions',{}))
state=JsonLayoutSession(request['graph'],selected);root=state.graph;marker=object()
state.computed_options.setdefault(id(root),{})['private.dispatch.marker']=marker
monitor=BasicProgressMonitor(logging=True);monitor.begin('dispatcher',1)
assert state.invoke_layout(root,algorithm,monitor)is True
assert len(monitor._children)==1
child=monitor._children[0];assert child.task_name==task and child._closed and child._parent is monitor
assert state.graph is root and state.property_snapshot(root).get_native('private.dispatch.marker')is marker
actual=state.export();comparison=diff(baseline['result'],actual,tolerant=False)
assert comparison['passed'],comparison
assert request==saved and not monitor._closed
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':True,'scope':'one registered private provider through real same-session dispatcher; saved direct-native equality, monitor and owned input',
 'algorithm':algorithm,'sourceSha256':before,'requestSha256':sha(request_path),'savedDirectNativeSha256':sha(baseline_path),
 'actualResult':actual,'entryComparison':comparison,'checkerSha256':sha(Path(__file__)),
 'childTask':child.task_name,'childClosed':child._closed,'sameSessionRoot':True,'markerRetained':True,
 'originalReexecuted':False,'publicAPIIntegrated':False,'wholeAlgorithmAccepted':False,'fullValidation':False},f,indent=2)
