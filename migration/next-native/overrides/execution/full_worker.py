"""Persistent native worker, transporting only owned JSON job envelopes."""
import os
import time

from .._errors import ValidationError,ExecutionError
from .runtime import NativeRuntime
from .worker import _ObservedTrace
from .wire_codec import encode_json_tree,decode_json_tree


def _summary(graph):
    nodes=ports=edges=labels=0
    pending=[graph]
    while pending:
        node=pending.pop()
        if type(node)is not dict:continue
        nodes+=1
        node_ports=node.get('ports',());node_edges=node.get('edges',());children=node.get('children',())
        if type(node_ports)not in(list,tuple):node_ports=()
        if type(node_edges)not in(list,tuple):node_edges=()
        node_labels=node.get('labels',())
        ports+=len(node_ports);edges+=len(node_edges)
        if type(node_labels)in(list,tuple):labels+=len(node_labels)
        for item in(*node_edges,*node_ports):
            if type(item)is dict and type(item.get('labels'))is list:labels+=len(item['labels'])
        if type(children)in(list,tuple):pending.extend(reversed(children))
    return{'nodes':nodes,'ports':ports,'edges':edges,'labels':labels}


def _execute(connection,runtime,job_id,graph,arguments):
    try:
        trace=_ObservedTrace(connection,job_id)
        entry={'index':0,'processor':'RecursiveLayoutEngine','before':_summary(graph),
               'after':{},'outcome':'running'}
        trace.append(entry)
        result=runtime.layout(graph,arguments)
        entry['after']=_summary(result);entry['outcome']='returned'
        connection.send({'kind':'result','job_id':job_id,'graph_tokens':encode_json_tree(result),'trace':list(trace),
                         'pid':os.getpid(),'process_time':time.process_time()})
    except ValidationError as error:
        connection.send({'kind':'error','job_id':job_id,'category':'validation',
                         'type':type(error).__name__,'code':error.code,
                         'path':error.path,'message':error.message})
    except ExecutionError as error:
        connection.send({'kind':'error','job_id':job_id,'category':'execution',
                         'type':type(error).__name__,'code':error.code,
                         'path':error.path,'message':error.message})
    except Exception as error:
        connection.send({'kind':'error','job_id':job_id,'category':'algorithm',
                         'type':type(error).__name__,'code':'WORKER_EXECUTION_FAILED',
                         'path':'','message':str(error)})


def worker_main(connection,constructor_tokens):
    try:
        runtime=NativeRuntime(decode_json_tree(constructor_tokens))
        while True:
            message=connection.recv()
            if message is None:return
            if type(message)is not dict or set(message)!={'job_id','graph_tokens','argument_tokens'}:
                raise ValueError('Invalid native worker request')
            _execute(connection,runtime,message['job_id'],decode_json_tree(message['graph_tokens']),
                     decode_json_tree(message['argument_tokens']))
    except(EOFError,BrokenPipeError,OSError):
        return
    finally:
        connection.close()
