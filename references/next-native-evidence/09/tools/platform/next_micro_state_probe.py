"""Targeted mutable-property and native identity host controls."""
from pathlib import Path
import argparse
import copy
import itertools
import json
import math
import os
import sys


def probe(workspace,case):
    sys.path.insert(0,str(Path(workspace)/'src'))
    import pyelk
    from pyelk.execution.json_transfer import JsonLayoutSession
    graph={'id':'root','children':[{'id':'a','$H':100,'ports':[{'id':'p'}]}, {'id':'b','$H':100}]}
    original=copy.deepcopy(graph);state=JsonLayoutSession(graph)
    a,b=state.graph['children'];port=a['ports'][0]
    if case=='provider-padding-materialization':
        from pyelk.algorithms import box,fixed
        for provider in (box,fixed):
            for options,expected in (({},15),({'elk.padding':'[top=3,right=4,bottom=5,left=6]'},6)):
                imported=JsonLayoutSession({'id':'r','layoutOptions':options,
                    'children':[{'id':'n','width':20,'height':10}]})
                root=imported.graph
                provider._layout(imported,root)
                assert imported.has_option(root,'padding')
                pad=imported.get_native_property(root,'padding')
                assert pad.left==expected
                imported.node_micro_layout(root)
                assert imported.get_native_property(root,'padding')is pad
                assert imported.read_native_property(root,'padding',factory=lambda:None,materialize=False)is pad
                assert imported.original['layoutOptions']==options
        skipped=JsonLayoutSession({'id':'r','layoutOptions':{'elk.nodeSize.fixedGraphSize':True}})
        fixed._layout(skipped,skipped.graph)
        assert not skipped.has_option(skipped.graph,'padding')
    elif case=='owner-default-property':
        from pyelk.options.schema import Padding
        imported=JsonLayoutSession({'id':'r','children':[{'id':'n','width':20,'height':10}]})
        root=imported.graph
        assert not imported.has_option(root,'padding')
        pad=imported.read_native_property(root,'padding',Padding(15,15,15,15))
        assert imported.has_option(root,'padding') and pad.left==15
        assert imported.get_native_property(root,'padding')is pad
        assert imported.read_native_property(root,'padding',Padding(8,8,8,8))is pad
        imported.node_micro_layout(root)
        assert imported.get_native_property(root,'padding')is pad and pad.left==15
        assert imported.read_native_property(root,'port.borderOffset')is None
        assert not imported.has_option(root,'port.borderOffset')
        assert 'padding'not in imported.original
    elif case=='native-property-getter':
        from pyelk.execution.node_micro import VectorChain
        from pyelk.algorithms.layered.graph import Vec2
        imported=JsonLayoutSession({'id':'r','children':[{'id':'x'},{'id':'y'}],
            'edges':[{'id':'e','sources':['x'],'targets':['y']}]})
        edge=imported.edges[0]
        assert not imported.has_option(edge,'junctionPoints')
        chain=imported.get_native_property(edge,'elk.junctionPoints')
        assert isinstance(chain,VectorChain)and not chain
        assert imported.has_option(edge,'junctionPoints')
        chain.append(Vec2(3,4))
        assert imported.get_native_property(edge,'org.eclipse.elk.junctionPoints')is chain
        assert imported.option(edge,'junctionPoints')==[{'x':3,'y':4}]
        assert imported.get_native_property(edge,'junctionPoints')is chain
        assert imported.property_snapshot(edge).get_native('junctionPoints')is chain
        assert 'junctionPoints'not in imported.original['edges'][0]
    elif case=='runtime-property-alias':
        imported=JsonLayoutSession({'id':'r'}, {'layered.crossingMinimization.strategy':'INTERACTIVE'})
        for spelling in ('crossingMinimization.strategy','layered.crossingMinimization.strategy',
                         'elk.layered.crossingMinimization.strategy','org.eclipse.elk.layered.crossingMinimization.strategy'):
            assert imported.has_option(imported.graph,spelling)
            assert imported.option(imported.graph,spelling)=='INTERACTIVE'
        assert imported.option(imported.graph,'private.providerScratch','caller-default')=='caller-default'
    elif case=='runtime-properties':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk.options.generic import RUNTIME_PROPERTY_SPECS
        from pyelk._errors import OptionValidationError
        model={'id':'r','labels':[{'text':'root label'}],
               'children':[{'id':'x','layoutOptions':{'alignment':'LEFT','font.name':'Local','contentAlignment':'V_TOP'},
                            'labels':[{'text':'child label'}],'ports':[{'id':'p'}]}, {'id':'y'}]}
        selected={'alignment':'CENTER','aspectRatio':'-1.25','font.name':'Inter','contentAlignment':'1,5',
                  'edgeRouting':3,'validateGraph':'FALSE','priority':'129'}
        before=copy.deepcopy(model);before_options=copy.deepcopy(selected)
        imported=JsonLayoutSession(model,selected);root=imported.graph;x,y=root['children'];p=x['ports'][0]
        reader=_PropertyReader(imported)
        assert len(RUNTIME_PROPERTY_SPECS)==243
        assert imported.option(x,'alignment')=='LEFT' and imported.option(y,'alignment')=='CENTER'
        assert imported.option(y,'elk.edgeRouting')=='SPLINES'
        assert imported.option(y,'org.eclipse.elk.aspectRatio')==-1.25
        assert imported.option(y,'priority')==129 and type(imported.option(y,'priority')) is int
        assert imported.has_option(root,'validateGraph') and imported.option(root,'validateGraph',True) is False
        assert not imported.has_option(p,'alignment') and imported.option(p,'alignment','none')=='none'
        assert imported.option(x,'font.name')=='Local', 'Local import must not apply global target filtering'
        assert not imported.has_option(root,'font.name')
        assert imported.option(root['labels'][0],'font.name')=='Inter'
        shared=reader.get(root,'node','contentAlignment')
        assert shared is reader.get(y,'node','contentAlignment') and shared=={'V_CENTER','H_RIGHT'}
        assert reader.get(x,'node','contentAlignment') is not shared
        shared.add('H_LEFT')
        assert 'H_LEFT' in reader.get(y,'node','contentAlignment')
        imported.set_option(y,'alignment','RIGHT');assert imported.option(y,'alignment')=='RIGHT'
        imported.remove_option(y,'alignment')
        assert not imported.has_option(y,'alignment') and imported.option(y,'alignment','caller-default')=='caller-default'
        assert model==before and selected==before_options
        empty_reader=_PropertyReader(state)
        assert empty_reader.get(a,'node','alignment')=='AUTOMATIC' and not state.has_option(a,'alignment')
        defaults=empty_reader.get(a,'node','contentAlignment')
        assert defaults=={'V_TOP','H_LEFT'} and defaults is empty_reader.get(b,'node','contentAlignment')
        assert not state.has_option(a,'contentAlignment')
        assert state.option(a,'aspectRatio',99)==99 and not state.has_option(a,'aspectRatio')
        try:JsonLayoutSession({'id':'invalid','layoutOptions':{'priority':'2147483648'}})
        except OptionValidationError:pass
        else:raise AssertionError('Imported invalid scalar was not validated')
    elif case=='core-property-defaults':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk.options.schema import generic_spec
        from pyelk.options.element import resolve_raw_element_options
        from pyelk.options.resolution import resolve_options
        from pyelk.execution.context import ExecutionContext
        reader=_PropertyReader(state)
        assert reader.get(a,'node','edgeRouting')=='UNDEFINED'
        assert reader.get(a,'node','separateConnectedComponents') is None
        assert not state.has_option(a,'edgeRouting') and not state.has_option(a,'separateConnectedComponents')
        assert reader.get(port,'port','port.borderOffset')==0.0
        assert not state.has_option(port,'port.borderOffset')
        context=ExecutionContext.create({'id':'context'})
        core=resolve_raw_element_options({},'node',context)
        assert core.values['org.eclipse.elk.edgeRouting']=='UNDEFINED'
        assert core.values['org.eclipse.elk.separateConnectedComponents'] is None
        for algorithm in ('layered','org.eclipse.elk.force','org.eclipse.elk.mrtree'):
            resolved=resolve_raw_element_options({},'node',context,algorithm=algorithm)
            assert resolved.values['org.eclipse.elk.separateConnectedComponents'] is True
        layered=resolve_raw_element_options({},'node',context,algorithm='layered')
        assert layered.values['org.eclipse.elk.edgeRouting']=='ORTHOGONAL'
        explicit=resolve_raw_element_options({'layoutOptions':{'elk.separateConnectedComponents':False}},'node',context,algorithm='layered')
        assert explicit.values['org.eclipse.elk.separateConnectedComponents'] is False
        bounded=resolve_options()
        assert bounded.values['org.eclipse.elk.edgeRouting']=='ORTHOGONAL'
        assert bounded.values['org.eclipse.elk.separateConnectedComponents'] is True
        assert generic_spec('org.eclipse.elk.port.borderOffset').declared_default==0.0
    elif case=='mutable-properties':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk.algorithms.fixed import _minimum, _padding
        reader=_PropertyReader(state)
        assert not reader.has(a,'node','direction')
        assert reader.get(a,'node','direction')=='UNDEFINED'
        assert not reader.has(a,'node','direction'), 'Primitive default was materialized'
        assert not reader.has(port,'port','port.borderOffset')
        assert reader.get(port,'port','port.borderOffset')==0
        assert not reader.has(port,'port','port.borderOffset'), 'Offset proxy changed actual presence'
        assert not reader.has(a,'node','nodeSize.minimum')
        value=reader.get(a,'node','nodeSize.minimum')
        assert reader.has(a,'node','nodeSize.minimum')
        assert reader.get(a,'node','nodeSize.minimum') is value
        sibling=reader.get(b,'node','nodeSize.minimum')
        assert sibling is not value and sibling.x==0
        value.x=9
        state.computed_options[id(a)]['nodeSize.constraints']={'MINIMUM_SIZE'}
        assert state.option(a,'nodeSize.minimum')=={'x':9,'y':0}
        assert _minimum(state,a)==(9,20), 'Actual fixed helper lost native mutable property values'
        padding=reader.get(a,'node','padding');padding.left=3
        assert _padding(state.option(a,'padding'))['left']==3
        assert reader.get(b,'node','padding').left==12
        flags=reader.get(a,'node','nodeSize.options')
        assert reader.get(a,'node','nodeSize.options') is flags
        result=state.export()
        assert 'layoutOptions' not in result['children'][0]
        assert result['children'][0]['$H']==100
    elif case=='wire-boundary':
        from pyelk._json import json_wire
        from pyelk._errors import ModelValidationError
        assert json_wire({'value':math.nan,'items':[math.inf,-math.inf,1,'NaN',True]}) == {
            'value':None,'items':[None,None,1,'NaN',True]}
        a['width']=math.nan;a['x']=math.inf
        result=state.export()
        assert result['children'][0]['width'] is None and result['children'][0]['x'] is None
        assert math.isnan(a['width']) and math.isinf(a['x']), 'Output conversion changed internal arithmetic'
        assert result['children'][0]['$H']==100
        json.dumps(result,allow_nan=False)
        try: JsonLayoutSession({'id':'invalid','width':math.nan})
        except ModelValidationError: pass
        else: raise AssertionError('Output wire conversion weakened input validation')
    elif case=='global-factory':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk._errors import OptionValidationError
        selected={'port.side':'NORTH','portLabels.treatAsGroup':'FALSE'}
        imported=JsonLayoutSession(graph,selected)
        selected['port.side']='WEST'
        reader=_PropertyReader(imported)
        first=imported.graph['children'][0];owned_port=first['ports'][0]
        assert reader.get(owned_port,'port','port.side')=='NORTH'
        assert reader.get(first,'node','port.side')=='UNDEFINED'
        assert reader.get(first,'node','portLabels.treatAsGroup') is False
        assert imported.options['port.side']=='NORTH'
        try: JsonLayoutSession(graph,False)
        except OptionValidationError: pass
        else: raise AssertionError('Invalid global factory container accepted')
    elif case=='native-identity':
        from pyelk.execution import identity
        first=state.identity_hash(a);second=state.identity_hash(b)
        assert type(first) is int and type(second) is int and first!=second
        assert state.identity_hash(a)==first and state.identity_hash(b)==second
        assert state.graph['children'][0]['$H']==state.graph['children'][1]['$H']==100
        # This isolated host control exercises signed32 wrap; runtime has no
        # fixture lookup or user JSON switch that changes the allocator.
        identity._CODES=itertools.count(0xffffffff)
        wrap=JsonLayoutSession({'id':'wrap'})
        values=[object(),object(),object()]
        assert [wrap.identity_hash(value) for value in values]==[-1,0,1]
        assert wrap.identity_hash(values[1])==0
    elif case=='property-presence':
        from pyelk.execution.node_micro import _PropertyReader, _Properties
        from pyelk._errors import OptionValidationError, UnsupportedOptionError
        model={'id':'r','layoutOptions':{'stress.desiredEdgeLength':75},
               'children':[{'id':'a','ports':[{'id':'p','layoutOptions':{'port.index':0}}]},
                           {'id':'b','layoutOptions':{'stress.fixed':'false'}}],
               'edges':[{'id':'e','sources':['a'],'targets':['b']}]}
        imported=JsonLayoutSession(model,{'port.side':'NORTH'})
        root=imported.graph;first,second=root['children'];p=first['ports'][0];edge=root['edges'][0]
        assert imported.has_option(root,'stress.desiredEdgeLength')
        assert imported.option(root,'stress.desiredEdgeLength')==75
        assert not imported.has_option(edge,'stress.desiredEdgeLength'), 'Parent local leaked onto edge'
        assert imported.option(edge,'stress.desiredEdgeLength',100)==100
        assert not imported.has_option(edge,'stress.desiredEdgeLength'), 'Fallback became explicit'
        imported.set_option(edge,'org.eclipse.elk.stress.desiredEdgeLength',0)
        assert imported.has_option(edge,'elk.stress.desiredEdgeLength')
        assert imported.option(edge,'stress.desiredEdgeLength',100)==0
        assert imported.has_option(second,'stress.fixed') and imported.option(second,'stress.fixed',True) is False
        assert imported.has_option(p,'port.index') and imported.option(p,'port.index')==0
        assert imported.has_option(p,'port.side') and imported.option(p,'port.side')=='NORTH'
        assert not imported.has_option(first,'port.side')
        assert imported.option(first,'port.side','UNDEFINED')=='UNDEFINED'
        imported.remove_option(p,'elk.port.side')
        assert not imported.has_option(p,'port.side') and imported.option(p,'port.side','UNDEFINED')=='UNDEFINED'
        imported.set_option(p,'port.side','WEST')
        assert imported.has_option(p,'port.side') and imported.option(p,'port.side')=='WEST'
        imported.set_option(p,'port.side',None)
        assert not imported.has_option(p,'port.side')
        props=_Properties(_PropertyReader(imported),first,'node')
        props['NODE_SIZE_FIXED_GRAPH_SIZE']=False
        assert imported.has_option(first,'nodeSize.fixedGraphSize')
        del props['NODE_SIZE_FIXED_GRAPH_SIZE']
        assert not imported.has_option(first,'nodeSize.fixedGraphSize')
        reader=_PropertyReader(imported)
        assert not imported.has_option(first,'nodeSize.minimum')
        reader.get(first,'node','nodeSize.minimum')
        assert imported.has_option(first,'nodeSize.minimum')
        assert not imported.has_option(first,'direction')
        reader.get(first,'node','direction')
        assert not imported.has_option(first,'direction')
        assert reader.get(first,'node','randomSeed') is None
        assert not imported.has_option(first,'randomSeed')
        duplicate=JsonLayoutSession({'id':'dup','layoutOptions':{'port.index':0,'elk.port.index':1}})
        try: duplicate.has_option(duplicate.graph,'port.index')
        except OptionValidationError as error: assert error.code=='AMBIGUOUS_OPTION'
        else: raise AssertionError('Ambiguous local aliases accepted')
        try: imported.has_option(first,'radial.radius')
        except UnsupportedOptionError: pass
        else: raise AssertionError('Unparsed targets guessed')
        exported=imported.export()
        assert 'layoutOptions' not in exported['edges'][0]
        assert exported['children'][0]['ports'][0]['layoutOptions']=={'port.index':0}
        assert model['edges'][0].get('layoutOptions') is None
    elif case=='cleared-property-replacement':
        from pyelk.execution.node_micro import _PropertyReader
        reader=_PropertyReader(state)
        state.cleared_constraints.add(id(a))
        assert state.has_option(a,'nodeSize.constraints')
        assert reader.get(a,'node','nodeSize.constraints')==set()
        state.set_option(a,'nodeSize.constraints',{'MINIMUM_SIZE'})
        assert id(a) not in state.cleared_constraints
        assert reader.get(a,'node','nodeSize.constraints')=={'MINIMUM_SIZE'}
        assert state.has_option(a,'nodeSize.constraints')
        state.cleared_constraints.add(id(a))
        state.remove_option(a,'nodeSize.constraints')
        assert id(a) not in state.cleared_constraints
        assert not state.has_option(a,'nodeSize.constraints')
        default=reader.get(a,'node','nodeSize.constraints')
        assert default==set() and not state.has_option(a,'nodeSize.constraints')
        assert reader.get(a,'node','nodeSize.constraints') is default
        default.add('PORTS')
        state.set_option(a,'nodeSize.constraints',None)
        assert not state.has_option(a,'nodeSize.constraints')
        assert reader.get(b,'node','nodeSize.constraints') is default
        assert default=={'PORTS'}, 'Shared source Core EnumSet default was cloned'
        default.clear()
    elif case=='cleared-set-mutation':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk.algorithms.fixed import _resize
        reader=_PropertyReader(state)
        _resize(state,a,10,10,False,False)
        constraints=reader.get(a,'node','nodeSize.constraints')
        constraints.add('MINIMUM_SIZE')
        assert reader.get(a,'node','nodeSize.constraints') is constraints
        assert reader.get(a,'node','nodeSize.constraints')=={'MINIMUM_SIZE'}
        assert state.option(a,'nodeSize.constraints')==['MINIMUM_SIZE']
        _resize(state,a,12,12,False,False)
        assert a['width']==20 and a['height']==20, 'Resize ignored the mutated explicit minimum constraint'
        refreshed=reader.get(a,'node','nodeSize.constraints')
        assert refreshed is not constraints and refreshed==set()
    elif case=='enumset-identity':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk.algorithms.fixed import _resize
        reader=_PropertyReader(state)
        first=reader.get(a,'node','nodeSize.options');second=reader.get(b,'node','nodeSize.options')
        assert first is second and not state.has_option(a,'nodeSize.options') and not state.has_option(b,'nodeSize.options')
        imported=JsonLayoutSession(graph,{'elk.nodeSize.options':'DEFAULT_MINIMUM_SIZE',
                                       'elk.nodeSize.minimum':'(3,4)'})
        x,y=imported.graph['children'];global_reader=_PropertyReader(imported)
        one=global_reader.get(x,'node','nodeSize.options');two=global_reader.get(y,'node','nodeSize.options')
        assert one is two and one is not first
        assert imported.has_option(x,'nodeSize.options') and imported.has_option(y,'nodeSize.options')
        assert global_reader.get(x,'node','nodeSize.minimum') is not global_reader.get(y,'node','nodeSize.minimum')
        local=JsonLayoutSession({'id':'local','children':[
            {'id':'x','layoutOptions':{'elk.nodeSize.options':'DEFAULT_MINIMUM_SIZE'}},
            {'id':'y','layoutOptions':{'elk.nodeSize.options':'DEFAULT_MINIMUM_SIZE'}}]})
        left,right=local.graph['children'];local_reader=_PropertyReader(local)
        assert local_reader.get(left,'node','nodeSize.options') is not local_reader.get(right,'node','nodeSize.options')
        _resize(imported,x,10,10,False,False)
        cleared=global_reader.get(x,'node','nodeSize.constraints')
        assert cleared is global_reader.get(x,'node','nodeSize.constraints')
        _resize(imported,x,12,12,False,False)
        assert global_reader.get(x,'node','nodeSize.constraints') is not cleared
        assert 'layoutOptions' not in state.export()['children'][0]
    elif case=='spore-invocation':
        model={'id':'r','layoutOptions':{'elk.algorithm':'box'},'children':[
            {'id':'a','x':0,'y':0,'width':20,'height':10},
            {'id':'b','x':80,'y':0,'width':20,'height':10},
            {'id':'c','x':0,'y':70,'width':20,'height':10},
            {'id':'d','x':80,'y':70,'width':20,'height':10}]}
        imported=JsonLayoutSession(model);root=imported.graph;child=root['children'][0]
        calls=[];actual=imported.calculate_node_margins
        def observe(node):calls.append(node['id']);return actual(node)
        imported.calculate_node_margins=observe
        def forbidden(node):raise AssertionError('Spore invocation used full micro')
        imported.node_micro_layout=forbidden
        assert imported.invoke_layout(root,'elk.sporeCompaction') is True
        assert calls==['r'] and imported.graph is root and root['children'][0] is child
        assert root['layoutOptions']['elk.algorithm']=='box'
        assert math.isfinite(root['width']) and math.isfinite(root['height'])
        assert root['width']>0 and root['height']>0
        assert model['children'][0]['x']==0 and 'width' not in model
    elif case=='label-minimum':
        model={'id':'outer','children':[{'id':'graph','x':3,'y':4,'width':10,'height':20,
                'layoutOptions':{'elk.nodeSize.constraints':'MINIMUM_SIZE,NODE_LABELS',
                                 'elk.nodeSize.minimum':'(15,16)',
                                 'elk.nodeLabels.placement':'INSIDE,H_CENTER,V_CENTER',
                                 'elk.portLabels.placement':'INSIDE',
                                 'elk.padding':'[top=2,right=3,bottom=4,left=5]'},
                'labels':[{'x':99,'y':88,'width':60,'height':10}],
                'ports':[{'id':'p','x':7,'y':8,'width':2,'height':3,'layoutOptions':{'elk.port.side':'WEST'},
                          'labels':[{'x':3,'y':4,'width':1000,'height':1000}]}]}]}
        imported=JsonLayoutSession(model);before=copy.deepcopy(imported.graph)
        value=imported.label_node_minimum(imported.graph['children'][0])
        assert value.x>=60 and value.y>=10 and value.x<500 and value.y<500
        assert imported.graph==before, 'Minimum adapter committed geometry/labels/ports'
        try:imported.label_node_minimum(imported.graph)
        except ValueError:pass
        else:raise AssertionError('Root took the parent-only source branch')
    elif case=='provider-invocation':
        from pyelk.execution.providers import algorithm_by_suffix
        from pyelk._errors import UnsupportedAlgorithmError
        model={'id':'r','layoutOptions':{'elk.algorithm':'sporeOverlap','elk.spacing.nodeNode':7,
                'elk.padding':'[top=2,right=3,bottom=4,left=5]'},
                'children':[{'id':'a','width':20,'height':10},{'id':'b','width':50,'height':20},
                            {'id':'c','width':10,'height':40}]}
        imported=JsonLayoutSession(model);root=imported.graph;first=root['children'][0]
        marker=object();imported.computed_options[id(root)]={'NATIVE_HOST_MARKER':marker}
        events=[]
        class Child:
            def begin(self,*args):events.append(('begin',args))
            def done(self):events.append(('done',))
        class Parent:
            def sub_task(self,work):events.append(('sub_task',work));return Child()
        assert algorithm_by_suffix('elk.box')=='org.eclipse.elk.box'
        for unknown in (None,'','ox','BOX','no-such-provider'):
            assert imported.invoke_layout(root,unknown,Parent()) is False
        assert events==[]
        try:imported.invoke_layout(root,'layered',Parent())
        except UnsupportedAlgorithmError:pass
        else:raise AssertionError('Known unavailable pipeline reported success')
        assert events==[]
        assert imported.invoke_layout(root,'elk.box',Parent()) is True
        assert events[0]==('sub_task',1) and events[-1]==('done',)
        assert imported.graph is root and root['children'][0] is first
        assert imported.computed_options[id(root)]['NATIVE_HOST_MARKER'] is marker
        assert root['width']==58 and root['height']==73
        assert root['layoutOptions']['elk.algorithm']=='sporeOverlap'
        assert 'width' not in model and model['children'][0].get('x') is None
    elif case=='identifier-view':
        identifiers=[7,'7',2**53+1,10**21,10**400]
        model={'id':'r','children':[{'id':value} for value in identifiers]}
        imported=JsonLayoutSession(model)
        assert [imported.identifier_text(n) for n in imported.graph['children']]==[
            '7','7','9007199254740992','1e+21','Infinity']
        assert imported.shapes[(int,7)] is not imported.shapes[(str,'7')]
        assert [n['id'] for n in imported.export()['children']]==identifiers
        assert model=={'id':'r','children':[{'id':value} for value in identifiers]}
    elif case=='double-storage':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk._errors import OptionValidationError
        reader=_PropertyReader(state)
        value=reader.get(a,'node','spacing.nodeNode')
        assert type(value) is float and value==20
        assert not state.has_option(a,'spacing.nodeNode')
        offset=reader.get(port,'port','port.borderOffset')
        assert type(offset) is float and offset==0
        assert not state.has_option(port,'port.borderOffset'), 'Offset proxy materialized presence'
        state.set_option(a,'force.temperature',2**53+1)
        value=state.option(a,'force.temperature')
        assert type(value) is float and value==2**53 and value+1==2**53
        state.computed_options[id(a)]['force.temperature']=2**53+1
        assert state.option(a,'force.temperature')==2**53
        state.set_option(a,'force.temperature',-0.0)
        assert math.copysign(1,state.option(a,'force.temperature'))<0
        state.set_option(a,'force.temperature',10**400)
        assert math.isinf(state.option(a,'force.temperature')), 'Generated nonfinite was clamped or rejected'
        try:JsonLayoutSession({'id':'wrong','layoutOptions':{'elk.force.temperature':10**400}})
        except OptionValidationError:pass
        else:raise AssertionError('DOUBLE storage weakened finite input validation')
    elif case=='spore-options':
        from pyelk.execution.node_micro import _PropertyReader
        from pyelk._errors import OptionValidationError
        model={'id':'r','layoutOptions':{'elk.processingOrder.rootSelection':0,
                'elk.processingOrder.preferredRoot':'a','elk.processingOrder.treeConstruction':1,
                'elk.processingOrder.spanningTreeCostFunction':4,'elk.overlapRemoval.maxIterations':-1},
                'children':[{'id':'a','ports':[{'id':'p'}]}]}
        imported=JsonLayoutSession(model,{'elk.compaction.orthogonal':'false','elk.overlapRemoval.runScanline':'false'})
        reader=_PropertyReader(imported);root=imported.graph;child=root['children'][0];p=child['ports'][0]
        assert imported.option(root,'processingOrder.rootSelection')=='FIXED'
        assert imported.option(root,'processingOrder.preferredRoot')=='a'
        assert imported.option(root,'processingOrder.treeConstruction')=='MAXIMUM_SPANNING_TREE'
        assert imported.option(root,'processingOrder.spanningTreeCostFunction')=='MINIMUM_ROOT_DISTANCE'
        assert imported.option(root,'overlapRemoval.maxIterations')==-1, 'Invented metadata lower bound'
        assert imported.option(root,'overlapRemoval.runScanline',True) is False
        assert imported.option(root,'compaction.orthogonal',True) is False
        assert not imported.has_option(p,'overlapRemoval.runScanline')
        assert not imported.has_option(child,'processingOrder.preferredRoot')
        assert reader.get(child,'node','processingOrder.rootSelection')=='CENTER_NODE'
        assert reader.get(child,'node','overlapRemoval.maxIterations')==64
        assert not imported.has_option(child,'overlapRemoval.maxIterations')
        imported.set_option(root,'underlyingLayoutAlgorithm','layered')
        assert imported.option(root,'underlyingLayoutAlgorithm')=='layered'
        for value in (False,1,'','null'):
            try:JsonLayoutSession({'id':'bad','layoutOptions':{'elk.processingOrder.preferredRoot':value}})
            except OptionValidationError:pass
            else:raise AssertionError('Invalid string property accepted')
        assert imported.original==model
    elif case=='host-entropy':
        from pyelk.execution import entropy
        # This one real host observation is a range check, never a golden draw.
        value=state.random_unit()
        assert type(value) is float and math.isfinite(value) and 0<=value<1
        original_random_bytes=entropy.os.urandom
        calls=[];samples=iter((bytes(8),bytes([255])*8))
        def bytes_control(count):
            calls.append(count)
            return next(samples)
        try:
            entropy.os.urandom=bytes_control
            first=JsonLayoutSession({'id':'one','layoutOptions':{'elk.randomSeed':7}})
            second=JsonLayoutSession({'id':'two','layoutOptions':{'elk.randomSeed':123}})
            assert first.random_unit()==0.0
            assert second.random_unit()==1.0-2**-53
            assert calls==[8,8]
        finally: entropy.os.urandom=original_random_bytes
    elif case=='margin-only':
        model={'id':'r','children':[{'id':'n','x':10,'y':20,'width':30,'height':40,
                'layoutOptions':{'elk.portConstraints':'FIXED_ORDER','elk.nodeSize.constraints':'PORTS,NODE_LABELS'},
                'labels':[{'id':'nl','x':-4,'y':-3,'width':5,'height':7}],
                'ports':[{'id':'east','x':35,'y':5,'width':10,'height':5,
                          'layoutOptions':{'elk.port.side':'EAST'},
                          'labels':[{'id':'pl','x':12,'y':-2,'width':8,'height':10}]},
                         {'id':'north','x':4,'y':3,'width':4,'height':3,
                          'layoutOptions':{'elk.port.side':'NORTH'}}]}]}
        imported=JsonLayoutSession(model);before=copy.deepcopy(imported.graph)
        assert imported.calculate_node_margins(imported.graph) is None
        child=imported.graph['children'][0]
        assert imported.graph==before, 'Margin-only call changed geometry/order'
        assert imported.option(child,'margins')=={'top':3,'right':25,'bottom':0,'left':4}
        assert [p['id'] for p in child['ports']]==['east','north']
        assert not imported.has_option(child,'nodeSize.minimum'), 'Full micro requested a size default'
        assert 'margins' not in model['children'][0]
    elif case=='source-option-additions':
        from pyelk.options.schema import generic_spec
        from pyelk.options.element import resolve_raw_element_options
        from pyelk.execution.context import ExecutionContext
        from pyelk.execution.node_micro import _PropertyReader
        model={'id':'r','layoutOptions':{'force.model':0,'force.iterations':'-2','force.temperature':'-0.5',
                                        'layered.considerModelOrder.strategy':3},
               'children':[{'id':'a','ports':[{'id':'p'}]}],
               'edges':[{'id':'e','sources':['a'],'targets':['a']} ]}
        imported=JsonLayoutSession(model,{'force.repulsivePower':0,'stress.desiredEdgeLength':'120',
                                           'layered.allowNonFlowPortsToSwitchSides':'false'})
        root=imported.graph;child=root['children'][0];p=child['ports'][0];edge=root['edges'][0]
        assert imported.option(root,'force.model')=='EADES'
        assert imported.option(root,'force.iterations')==-2
        assert imported.option(root,'force.temperature')==-0.5
        assert imported.option(root,'layered.considerModelOrder.strategy')=='PREFER_NODES'
        assert not imported.has_option(root,'force.repulsivePower')
        assert imported.has_option(edge,'force.repulsivePower') and imported.option(edge,'force.repulsivePower')==0
        assert imported.option(edge,'stress.desiredEdgeLength')==120
        assert imported.option(root,'stress.desiredEdgeLength')==120
        assert not imported.has_option(p,'stress.desiredEdgeLength')
        assert imported.has_option(p,'layered.allowNonFlowPortsToSwitchSides')
        assert imported.option(p,'layered.allowNonFlowPortsToSwitchSides',True) is False
        reader=_PropertyReader(imported)
        assert reader.get(root,'node','stress.dimension')=='XY'
        assert not imported.has_option(root,'stress.dimension')
        assert generic_spec('org.eclipse.elk.priority').declared_default is None
        assert generic_spec('org.eclipse.elk.randomSeed').declared_default is None
        assert generic_spec('org.eclipse.elk.edgeLabels.inline').declared_default is False
        # Element importer and generic provider adapter use the same Core
        # schema, while the old bounded parser remains a distinct surface.
        context=ExecutionContext.create({'id':'context'})
        resolved=resolve_raw_element_options({'layoutOptions':{'elk.padding':'[left=3]','elk.direction':1}},'node',context)
        assert resolved.values['org.eclipse.elk.padding'].left==3
        assert resolved.values['org.eclipse.elk.padding'].right==0
        assert resolved.values['org.eclipse.elk.direction']=='RIGHT'
        assert resolved.values['org.eclipse.elk.randomSeed'] is None
        force=resolve_raw_element_options({},'node',context,algorithm='org.eclipse.elk.force')
        assert force.values['org.eclipse.elk.priority']==1 and force.values['org.eclipse.elk.randomSeed']==1
        stress=resolve_raw_element_options({},'label',context,algorithm='org.eclipse.elk.stress')
        assert stress.values['org.eclipse.elk.edgeLabels.inline'] is False
    else: raise ValueError('Unknown native micro host control')
    assert graph==original
    return {'passed':True,'case':case,'privateSource':True,'modulePath':str(Path(pyelk.__file__).resolve()),
            'pid':os.getpid(),'parentPid':os.getppid(),'publicAPIIntegrated':False,'fullValidation':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True,type=Path);parser.add_argument('--case',required=True)
    args=parser.parse_args();print(json.dumps(probe(args.workspace,args.case)))
