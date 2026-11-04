"""Exercise one private source-option case in an isolated interpreter namespace."""
from pathlib import Path
import argparse
import copy
import json
import sys


def probe(workspace,case):
    sys.path.insert(0,str(Path(workspace)/'src'))
    import pyelk
    from pyelk.execution.context import create_context
    from pyelk._errors import OptionValidationError
    prefix='org.eclipse.elk.'
    graph={'id':'root','layoutOptions':{'portConstraints':'FIXED_SIDE'},'children':[
        {'id':'a','width':30,'height':20,'layoutOptions':{'portConstraints':'FIXED_POS'},
         'ports':[{'id':'p','layoutOptions':{'port.side':'NORTH','port.borderOffset':0}}]},
        {'id':'b','width':20,'height':10,'ports':[{'id':'q'}]}]}
    before=copy.deepcopy(graph)
    if case=='precedence':
        c=create_context(graph,constructor={'defaultLayoutOptions':{
            'portConstraints':'FIXED_RATIO','port.side':'EAST','port.borderOffset':-2}})
        root,a,b=c.working_graph.nodes;p,q=a.ports[0],b.ports[0]
        assert c.element_options(root).values[prefix+'portConstraints']=='FIXED_SIDE'
        assert c.element_options(a).values[prefix+'portConstraints']=='FIXED_POS'
        assert c.element_options(b).values[prefix+'portConstraints']=='FIXED_RATIO'
        options=c.element_options(p);other=c.element_options(q)
        assert options.values[prefix+'port.side']=='NORTH' and options.values[prefix+'port.borderOffset']==0
        assert options.origins[prefix+'port.borderOffset']=='local' and prefix+'port.borderOffset' in options.raw_values
        assert other.values[prefix+'port.borderOffset']==-2 and other.origins[prefix+'port.borderOffset']=='constructor'
    elif case=='call-replacement':
        c=create_context(graph,constructor={'defaultLayoutOptions':{'port.side':'WEST','port.index':6}},
                         layout_arguments={'layoutOptions':{}})
        b=c.working_graph.nodes[2];options=c.element_options(b.ports[0])
        assert options.values[prefix+'port.side']=='UNDEFINED' and options.values[prefix+'port.index'] is None
        assert options.origins[prefix+'port.index']=='default' and prefix+'port.index' not in options.raw_values
        assert c.element_options(b).values[prefix+'portConstraints']=='UNDEFINED'
    elif case=='typed':
        graph['children'][0]['ports'][0]['layoutOptions']={
            'port.side':3.0,'port.index':'0','port.anchor':'[1;2]','port.borderOffset':'-2.5'}
        before=copy.deepcopy(graph)
        c=create_context(graph,constructor={'defaultLayoutOptions':{'port.anchor':[4,5]}})
        a,b=c.working_graph.nodes[1:];options=c.element_options(a.ports[0]);other=c.element_options(b.ports[0])
        assert options.values[prefix+'port.side']=='SOUTH' and options.values[prefix+'port.index']==0
        assert options.values[prefix+'port.anchor'].x==1 and options.values[prefix+'port.anchor'].y==2
        assert other.values[prefix+'port.anchor'].x==4 and other.values[prefix+'port.anchor'].y==5
        assert options.values[prefix+'port.borderOffset']==-2.5 and options.raw_values[prefix+'port.index']=='0'
    elif case=='invalid':
        for raw in ({'port.index':False},{'port.index':2**31},{'port.side':'east'},
                    {'port.anchor':[1,2]},{'port.anchor':{'x':1,'y':2}},{'port.borderOffset':'NaN'},
                    {'port.side':'NORTH','elk.port.side':'WEST'}):
            value=copy.deepcopy(graph);value['children'][0]['ports'][0]['layoutOptions']=raw
            c=create_context(value)
            try:c.element_options(c.working_graph.nodes[1].ports[0])
            except OptionValidationError:pass
            else:raise AssertionError('Invalid/private ambiguous option was accepted: '+repr(raw))
    else:raise ValueError('Unknown source-option probe')
    assert graph==before,'Private option parsing mutated original graph'
    return {'case':case,'passed':True,'privateSource':True,'modulePath':str(Path(pyelk.__file__).resolve()),
            'publicAPIIntegrated':False,'fullValidation':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--case',required=True);args=parser.parse_args()
    print(json.dumps(probe(args.workspace,args.case)))
