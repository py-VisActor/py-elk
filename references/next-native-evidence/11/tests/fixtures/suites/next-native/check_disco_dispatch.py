"""PRIVATE_SRC REQUEST SAVED_DIRECT_NATIVE NEW_REPORT; new dispatcher entry only."""
import copy,hashlib,json,sys
from pathlib import Path
source,request_path,baseline_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from layout_checks import diff
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.diagnostics import BasicProgressMonitor
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));baseline=json.loads(baseline_path.read_text('utf-8'))
saved=copy.deepcopy(request)
assert baseline['sourceWireParity']is True and baseline['validFiniteGeometry']is True and not baseline['mandatoryDifferences']
arguments=request.get('layoutArguments',{});constructor=request.get('constructor',{})
selected=arguments.get('layoutOptions',constructor.get('defaultLayoutOptions',{}))
state=JsonLayoutSession(request['graph'],selected);root=state.graph;marker=object()
state.computed_options.setdefault(id(root),{})['private.dispatch.marker']=marker
monitor=BasicProgressMonitor(logging=True);monitor.begin('dispatcher',1)
assert state.invoke_layout(root,'elk.disco',monitor)is True
assert len(monitor._children)==1
child=monitor._children[0]
assert child.task_name=='Connected Components Compaction'and child._closed and child._parent is monitor
assert state.graph is root and state.property_snapshot(root).get_native('private.dispatch.marker')is marker
actual=state.export();comparison=diff(baseline['result'],actual,tolerant=False)
assert comparison['passed'],comparison
# Export writes the session's owned original JSON; caller input stays separate.
assert request==saved and not monitor._closed
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':True,'scope':'new private same-session DisCo dispatcher/monitor entry; one actual request equals its saved direct native result',
 'sourceSha256':before,'requestSha256':sha(request_path),'savedDirectNativeSha256':sha(baseline_path),
 'actualResult':actual,'entryComparison':comparison,'checkerSha256':sha(Path(__file__)),
 'childTask':child.task_name,'childClosed':child._closed,'sameSessionRoot':True,'markerRetained':True,
 'originalReexecuted':False,'publicAPIIntegrated':False,'wholeAlgorithmAccepted':False,'fullValidation':False},f,indent=2)
