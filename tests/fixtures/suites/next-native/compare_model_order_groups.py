"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; only assigned unique CB groups."""
import hashlib,json,sys
from pathlib import Path
source,request_path,oracle_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.algorithms.layered.graph import LGraph,LNode
from pyelk.algorithms.layered.model_order_import import import_flat_model_order,bind_model_order
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
oracle=json.loads(oracle_path.read_text('utf-8'));assert sha(request_path)==oracle['requestSha256']
state=JsonLayoutSession(json.loads(request_path.read_text('utf-8')));graph=LGraph(None,None,None)
def transform_node(raw):
    node=LNode(graph);bind_model_order(state,raw,node);graph.layerless_nodes.append(node)
import_flat_model_order(state,state.graph,graph,transform_node=transform_node,transform_edge=lambda edge:None)
a,b=state.graph['children'][:2];group='layered.considerModelOrder.groupModelOrder.cycleBreakingId'
actual={'groups':graph.properties['CB_NUM_MODEL_ORDER_GROUPS'],'maximum':graph.properties['MAX_MODEL_ORDER_NODES'],
 'equalGroupDistinctBoxes':state.integer_box_identity(a,group,None)is not state.integer_box_identity(b,group,None),
 'importedNodes':len(graph.layerless_nodes)}
comparison=diff(oracle['observation'],actual)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'sourceSha256':before,'oracleSha256':sha(oracle_path),'scope':'assigned explicit numeric groups only; no complete importer/layout claim','fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
