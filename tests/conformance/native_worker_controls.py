"""Test-only spawn targets: guards and deliberate faults live in the CPU child.

The parent may spawn its native Python worker. Inside that worker the real
kernel retains the original prohibition on launching any external engine.
Faults never change production code, fixtures, expected results or geometry.
"""
from unittest.mock import patch

EXTERNAL_ENGINE_GUARD = "Native kernel must not launch an external engine"


def _noop(work):
    """The same deliberately omitted operation as the original parent patch."""


def _run_guarded(connection, constructor_tokens, omitted=None, external=False):
    from pyelk.execution.full_worker import worker_main
    from pyelk.algorithms.layered.algorithm_assembler import AlgorithmAssembler
    from pyelk.execution.runtime import NativeRuntime
    from full_trace_observer import Observer
    observer = Observer()
    real_build = AlgorithmAssembler.build
    def build(assembler, graph):
        return [observer.wrap(processor, omitted) for processor in real_build(assembler,graph)]
    class ObservedConnection:
        def recv(self):
            value=connection.recv()
            if isinstance(value,dict)and'job_id'in value:
                observer.ids={'node':{},'port':{},'edge':{}}
                observer.trace.clear()
                def progress(row):
                    import time
                    previous=observer.trace[-2]if len(observer.trace)>1 else None
                    connection.send({'kind':'progress','job_id':value['job_id'],'index':row['index'],
                        'processor':row['processor'],'previous_processor':None if previous is None else previous['processor'],
                        'previous_outcome':None if previous is None else previous['outcome'],
                        'process_time':time.process_time()})
                observer.progress=progress
            return value
        def send(self,value):
            if isinstance(value,dict)and value.get('kind')=='progress':return
            if isinstance(value,dict)and value.get('kind')=='result':
                value={**value,'trace':observer.trace}
            return connection.send(value)
        def close(self):return connection.close()
    with patch("subprocess.Popen", side_effect=AssertionError(EXTERNAL_ENGINE_GUARD)):
        with patch.object(AlgorithmAssembler,'build',build):
            if external:
                with patch.object(NativeRuntime,'layout',_attempt_external_process):
                    worker_main(ObservedConnection(),constructor_tokens)
            else:
                worker_main(ObservedConnection(),constructor_tokens)


def guarded_worker(connection, constructor_tokens):
    _run_guarded(connection, constructor_tokens)


def without_node_spacing_worker(connection, constructor_tokens):
    _run_guarded(connection, constructor_tokens, "LabelAndNodeSizeProcessor")


def without_loop_postprocessor_worker(connection, constructor_tokens):
    _run_guarded(connection, constructor_tokens, "SelfLoopPostProcessor")


def without_reversed_restorer_worker(connection, constructor_tokens):
    _run_guarded(connection, constructor_tokens, "ReversedEdgeRestorer")


def _attempt_external_process(self, graph, arguments=None):
    import subprocess
    import sys
    # The guard must reject before creating this harmless Python process.
    # If it is accidentally missing, the different protocol/error below cannot
    # satisfy the test's exact guard message and execution-error assertions.
    child=subprocess.Popen([sys.executable, "-c", "raise SystemExit(0)"])
    child.wait(timeout=5)


def attempted_external_process_worker(connection, constructor_tokens):
    _run_guarded(connection, constructor_tokens, external=True)


def instrument_kernel(graph, constructor, arguments):
    """Only a phase-instrumentation test bypasses scheduling, explicitly.

    Its parent-side callback contains TestCase assertions and observes writes
    in the same process. All ordinary conformance observations use public ELK
    and guarded_worker; lifecycle acceptance never uses this helper.
    """
    from pyelk.execution.context import create_context
    from pyelk.algorithms.layered.scope import validate_slice
    from pyelk.algorithms.layered.pipeline import layout_context
    with patch("subprocess.Popen", side_effect=AssertionError(EXTERNAL_ENGINE_GUARD)):
        context=create_context(graph, constructor=constructor, layout_arguments=arguments)
        validate_slice(context)
        return layout_context(context, trace=[])
