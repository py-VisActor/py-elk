"""PRIVATE_SRC REQUEST ORIGINAL REPORT; actual comment pre/margin/post objects."""
import hashlib
import json
import sys
from pathlib import Path

source, request_path, original_path, out = map(Path, sys.argv[1:5])
sys.path.insert(0, str(source.resolve()))
sys.path.insert(0, str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered import comments_general as comments
from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Layer, Vec2, set_port_owner, set_source, set_target, set_layer
from pyelk.algorithms.layered.native_import import LLabel
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap, canonical_property_key
from pyelk.algorithms.layered.ports import set_side
from pyelk.execution.node_micro import VectorChain

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
original = json.loads(original_path.read_bytes())
request = json.loads(request_path.read_bytes())
assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256'] == sha(request_path)
assert original['probeSha256'] == sha(Path(__file__).with_name('comment-context-probe.cjs'))
before = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*.py')}

def graph():
    result = LGraph(None, None, None)
    result.properties = CanonicalPropertyMap()
    return result

def node(g):
    return LNode(g, properties=CanonicalPropertyMap())

def margin(n):
    return [n.margin.top, n.margin.right, n.margin.bottom, n.margin.left]

def vec(value):
    return [value.x, value.y]

class Monitor:
    record_logs = True
    def __init__(self, events): self.events = events
    def begin(self, name, work): self.events.append(['begin', name, work])
    def done(self): self.events.append(['done'])
    def is_logging_enabled(self): return True
    def log(self, text): self.events.append(['log', text])

margin_cases = []
for index, name in enumerate(request['marginCases']):
    g = graph(); n = node(g); layer = Layer(g); events = []; reads = []
    g.layers.append(layer); set_layer(n, layer)
    n.size.x = 1.0 if index == 1 else 5.0
    n.margin.top = 1.0; n.margin.right = 1.0; n.margin.bottom = 4.0; n.margin.left = 2.0
    g.properties.update({'SPACING_COMMENT_COMMENT': 10, 'SPACING_COMMENT_NODE': 10})
    old_margin = n.margin; top = []; bottom = []
    if index == 0:
        n.properties._values[canonical_property_key('SPACING_INDIVIDUAL')] = None
    if index == 1:
        n.properties['SPACING_INDIVIDUAL'] = {'org.eclipse.elk.spacing.commentComment': -4,
                                             'org.eclipse.elk.spacing.commentNode': 3}
        n.properties['TOP_COMMENTS'] = top
    if index == 2:
        for width, height in [(4, 2), (7, 5)]:
            box = node(g); box.size = Vec2(float(width), float(height)); top.append(box)
        n.properties.update({'TOP_COMMENTS': top, 'BOTTOM_COMMENTS': bottom, 'SPACING_INDIVIDUAL': {}})
    old = comments.get_individual_or_default
    def read(holder, selected):
        reads.append('commentComment' if selected.symbol == 'SPACING_COMMENT_COMMENT' else 'commentNode')
        return old(holder, selected)
    comments.get_individual_or_default = read
    values = []
    try:
        for _ in range(request['repeatMargin']):
            comments.comment_node_margin_calculator(g, monitor=Monitor(events)); values.append(margin(n))
    finally:
        comments.get_individual_or_default = old
    margin_cases.append(dict(name=name, events=events, reads=reads, values=values,
                             sameMargin=n.margin is old_margin,
                             sameTop=n.properties.get('TOP_COMMENTS') is (None if index == 0 else top),
                             sameBottom=n.properties.get('BOTTOM_COMMENTS') is (bottom if index == 2 else None),
                             size=vec(n.size), topPresence='TOP_COMMENTS' in n.properties,
                             bottomPresence='BOTTOM_COMMENTS' in n.properties))

pre_cases = []
for case in request['preCases']:
    g = graph(); nodes = []; ports = []; edges = []; names = {}; events = []
    dummy_layers = []; notes = []; connections = []; bends = []; initial_top = []; initial_bottom = []
    def new_node(name):
        n = node(g); names[n] = name; nodes.append(n); g.layerless_nodes.append(n); return n
    def port(owner, name, side):
        p = LPort(properties=CanonicalPropertyMap()); set_port_owner(p, owner); set_side(p, side)
        p.anchor = Vec2(.75, .5); names[p] = name; ports.append(p); return p
    def edge(start, end, name):
        e = LEdge(properties=CanonicalPropertyMap()); set_source(e, start); set_target(e, end)
        names[e] = name; edges.append(e); e.bend_points = VectorChain([Vec2(1.0, 2.0), Vec2(3.0, 4.0)])
        bends.append(e.bend_points); return e
    real = new_node('real'); neighbor = new_node('neighbor')
    real.size = Vec2(20.0, 10.0); real.pos = Vec2(30.0, 50.0)
    real.margin.top = 1.0; real.margin.right = 2.0; real.margin.bottom = 3.0; real.margin.left = 4.0
    g.properties.update({'SPACING_COMMENT_COMMENT': 4, 'SPACING_COMMENT_NODE': 6})
    real.properties.update({'PORT_CONSTRAINTS': 'FIXED_SIDE' if case['fixed'] else 'FREE',
                            'TOP_COMMENTS': initial_top, 'BOTTOM_COMMENTS': initial_bottom})
    label = LLabel(None); label.pos.y = 0.0; label.size.y = 2.0; real.labels.append(label)
    for side in case['sideOrder']:
        edge(port(real, 'real-' + side, side), port(neighbor, 'neighbor-' + side, 'WEST'), 'neighbor-' + side)
    for index in range(case['noteCount']):
        note = new_node('note' + str(index)); notes.append(note); note.properties['COMMENT_BOX'] = True
        note.size = Vec2(float([7, 9, 5][index]), float([3, 5, 2][index]))
        bp = port(note, 'box' + str(index), 'EAST'); np = port(real, 'connection' + str(index), 'WEST'); connections.append(np)
        edge(bp if case['noteOutgoing'] else np, np if case['noteOutgoing'] else bp, 'comment' + str(index))
        dummy = node(g); layer = Layer(g); names[dummy] = 'dummy' + str(index); nodes.append(dummy)
        g.layers.append(layer); set_layer(dummy, layer); dummy_layers.append(layer); np.properties['PORT_DUMMY'] = dummy
    retained = new_node('retained-loop'); retained.properties['COMMENT_BOX'] = True
    rp = port(retained, 'loop-port', 'NORTH'); loop = edge(rp, rp, 'loop')
    ll = LLabel(None); ll.properties = CanonicalPropertyMap({'EDGE_LABELS_PLACEMENT': 'HEAD'}); loop.labels.append(ll)
    loop_points = list(loop.bend_points)
    def named(value): return None if value is None else names.get(value)
    def bag(key):
        values = real.properties.get(key)
        return None if values is None else [named(v) for v in values]
    def view():
        return dict(layerless=[named(n) for n in g.layerless_nodes], layers=[[named(n) for n in l.nodes] for l in g.layers],
                    realPorts=[named(p) for p in real.ports], top=bag('TOP_COMMENTS'), bottom=bag('BOTTOM_COMMENTS'), margin=margin(real),
                    notes=[dict(name=named(n), pos=vec(n.pos), boxPort=vec(n.ports[0].pos), connectionOwner=named(connections[i].owner),
                                connectionPos=vec(connections[i].pos), storedConnection=n.properties.get('COMMENT_CONN_PORT') is connections[i],
                                sameGraph=n.graph is g) for i, n in enumerate(notes)],
                    edges=[dict(name=named(e), source=named(e.source), target=named(e.target), bends=[vec(p) for p in e.bend_points],
                                sameBendChain=e.bend_points is bends[i]) for i, e in enumerate(edges)],
                    dummyLayerPointers=[next(n for n in nodes if names[n] == 'dummy' + str(i)).layer is l for i, l in enumerate(dummy_layers)],
                    loop=dict(reversed=loop.properties.get('REVERSED', False), present='REVERSED' in loop.properties,
                              label=ll.properties.get('EDGE_LABELS_PLACEMENT'), samePoints=[p is loop_points[i] for i, p in enumerate(loop.bend_points)]),
                    sameTop=real.properties.get('TOP_COMMENTS') is initial_top, sameBottom=real.properties.get('BOTTOM_COMMENTS') is initial_bottom)
    comments.comment_preprocessor(g, monitor=Monitor(events)); pre = view()
    main_layer = Layer(g); g.layers.append(main_layer)
    for n in g.layerless_nodes: set_layer(n, main_layer)
    g.layerless_nodes.clear()
    comments.comment_node_margin_calculator(g, monitor=Monitor(events)); margined = view(); posts = []
    for _ in range(request['repeatPost']):
        comments.comment_postprocessor(g, monitor=Monitor(events)); posts.append(view())
    pre_cases.append(dict(name=case['name'], events=events, pre=pre, margined=margined, posts=posts))

actual = dict(marginCases=margin_cases, preCases=pre_cases)
comparison = diff(original['value'], actual, tolerant=False)
assert before == {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*.py')}
with out.open('x', encoding='utf8') as stream:
    json.dump(dict(passed=comparison['passed'], comparison=comparison, actual=actual, sourceFilesSha256=before,
                   requestSha256=sha(request_path), originalSha256=sha(original_path), checkerSha256=sha(Path(__file__)),
                   layoutExecuted=False, explicitGeometrySetup=True, fullValidation=False), stream, indent=2)
print(json.dumps(dict(passed=comparison['passed'], differences=len(comparison['differences']))))
raise SystemExit(0 if comparison['passed'] else 1)
