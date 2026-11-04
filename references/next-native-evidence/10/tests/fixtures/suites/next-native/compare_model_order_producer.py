"""PRIVATE_SRC ORACLE NEW_REPORT; producer/predicate only, not full import."""
import hashlib,json,os,sys
from pathlib import Path
source,oracle_path,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,set_port_owner
from pyelk.algorithms.layered.model_order_import import needs_model_order,bind_model_order,transform_ordered_ports,import_flat_model_order
from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
oracle=json.loads(oracle_path.read_text('utf-8'));predicates=[]
for case in oracle['observation']['predicates']:
    state=JsonLayoutSession({'id':'r','layoutOptions':case['options']})
    predicates.append({'options':case['options'],'needed':needs_model_order(state,state.graph)})
    assert not state.property_snapshot(state.graph).values.keys()-{
        key[len('elk.'):]for key in case['options']}
# Same literal graph as the original probe; this comparator binds its bytes.
probe=Path(__file__).with_name('model-order-producer-probe.cjs');assert sha(probe)==oracle['probeSha256']
model={'id':'r','layoutOptions':{'elk.layered.crossingMinimization.forceNodeModelOrder':True},'children':[
 {'id':'skip','layoutOptions':{'elk.noLayout':True}},
 {'id':'excluded','layoutOptions':{'elk.layered.considerModelOrder.noModelOrder':True},'ports':[{'id':'xp'}]},
 {'id':'c','ports':[{'id':'p0','layoutOptions':{'elk.noLayout':True}},{'id':'p1'}]},
 {'id':'d'}],'edges':[{'id':'e0','sources':['c'],'targets':['d'],'layoutOptions':{'elk.noLayout':True}},
                    {'id':'e1','sources':['c'],'targets':['d']}]}
state=JsonLayoutSession(model);root=state.graph;native=LGraph(None,None,None)
def transform_node(raw):
    node=LNode(native);native.layerless_nodes.append(node);bind_model_order(state,raw,node)
    def transform_port(raw_port):
        port=LPort();set_port_owner(port,node);bind_model_order(state,raw_port,port)
    transform_ordered_ports(state,raw,transform_port)
import_flat_model_order(state,root,native,transform_node=transform_node,transform_edge=lambda edge:None)
order=lambda raw:state.property_snapshot(raw).get_native('modelOrder')
actual={'predicates':predicates,'nodes':[[n['id'],order(n)]for n in root['children']],
 'ports':[[p['id'],order(p)]for n in root['children']for p in n.get('ports',[])],
 'edges':[[e['id'],order(e)]for e in root['edges']],'maximum':native.properties['MAX_MODEL_ORDER_NODES'],
 'importedNodeCount':len(native.layerless_nodes)}
assert native.layerless_nodes[1].properties['MODEL_ORDER']==0
assert len(native.layerless_nodes[1].ports)==1 and native.layerless_nodes[1].ports[0].properties['MODEL_ORDER']==1
assert native.layerless_nodes[1].integer_box_identities['MODEL_ORDER']is value_of_integer_box(0)
assert native.integer_box_identities['MAX_MODEL_ORDER_NODES']is value_of_integer_box(2)
assert native.properties['CB_NUM_MODEL_ORDER_GROUPS']==0
assert state.original==model
comparison=diff(oracle['observation'],actual)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'sourceSha256':before,'oracleSha256':sha(oracle_path),'probeSha256':sha(probe),'pid':os.getpid(),'parentPid':os.getppid(),
 'scope':'16 predicates and actual producer guard/order; transform callbacks exercise native holder binding only; no full geometry/endpoint importer',
 'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
