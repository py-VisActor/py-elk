"""Separate, explicitly instrumented installed-worker samples for E10.

These are explanatory intervals, never samples of uninstrumented throughput.
The original worker and IPC execute unchanged inside the private target wrapper.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def load_benchmark():
    spec = importlib.util.spec_from_file_location('e10_public_benchmark', Path(__file__).with_name('benchmark_e10.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class Intervals:
    """Record nested monotonic wall and process CPU intervals once each."""
    def __init__(self):
        self.spans = []

    def begin(self, kind, name, parent=None):
        item = {'id': len(self.spans), 'kind': kind, 'name': name, 'parentSpanId': parent,
                'startNs': time.perf_counter_ns(), 'startCpuNs': time.process_time_ns()}
        self.spans.append(item)
        return item

    def done(self, item):
        if 'finishNs' in item:
            raise ValueError('Instrumentation span closed twice')
        item.update(finishCpuNs=time.process_time_ns(), finishNs=time.perf_counter_ns())

    def current(self):
        return next((item['id'] for item in reversed(self.spans) if 'finishNs' not in item), None)


def instrumented_worker(connection, job_id, graph, constructor, arguments):
    """Spawn-importable target; no proxy or transformation of original messages."""
    from pyelk.execution.worker import run_job
    from pyelk.execution.diagnostics import BasicProgressMonitor
    from pyelk.algorithms.layered import pipeline, import_export
    intervals = Intervals(); monitors = {}
    begin, done = BasicProgressMonitor.begin, BasicProgressMonitor.done
    layout = pipeline.layout_context
    imported, exported = import_export.import_raw_graph, import_export.export_layout

    def observed_begin(monitor, name, total_work):
        accepted = begin(monitor, name, total_work)
        if accepted:
            parent = monitors.get(id(monitor._parent))
            monitors[id(monitor)] = intervals.begin('monitor', name, intervals.current() if parent is None else parent['id'])
        return accepted

    def observed_done(monitor):
        was_running = monitor.is_running()
        result = done(monitor)
        if was_running:
            intervals.done(monitors[id(monitor)])
        return result

    def observed_layout(context, *, trace=None, monitor=None):
        # All public benchmark requests use false/absent flags. This private
        # observer requests real caller boundaries without generated graph logs.
        if monitor is None:
            monitor = BasicProgressMonitor(False, False)
        return layout(context, trace=trace, monitor=monitor)

    def boundary(original, name):
        def observed(*args, **kwargs):
            item = intervals.begin('transport', name, intervals.current())
            try:
                return original(*args, **kwargs)
            finally:
                intervals.done(item)
        return observed

    BasicProgressMonitor.begin, BasicProgressMonitor.done = observed_begin, observed_done
    pipeline.layout_context = observed_layout
    import_export.import_raw_graph = boundary(imported, 'import_raw_graph')
    import_export.export_layout = boundary(exported, 'export_layout')
    whole = intervals.begin('worker', 'original run_job')
    try:
        run_job(connection, job_id, graph, constructor, arguments)
    finally:
        intervals.done(whole)
        BasicProgressMonitor.begin, BasicProgressMonitor.done = begin, done
        pipeline.layout_context = layout
        import_export.import_raw_graph, import_export.export_layout = imported, exported
        value = {'schema': 'py-elk-e10-worker-intervals/v1', 'pid': os.getpid(), 'jobId': job_id,
                 'clocks': {'elapsed': 'time.perf_counter_ns', 'cpu': 'time.process_time_ns'},
                 'spans': intervals.spans, 'workerSpanId': whole['id'],
                 'limitations': ['Nested intervals overlap: no summing parent and child spans.',
                                 'Routing is a subset of phase intervals, not an additional additive cost.',
                                 'Sidecar serialization follows the original worker interval.']}
        load_benchmark().save(os.environ['PY_ELK_E10_SIDECAR'], value)


async def sample(wheel, request, output):
    public = load_benchmark()
    from pyelk.execution.lifecycle import ExecutionController
    original = ExecutionController.__init__
    def constructor(controller, *args, **kwargs):
        original(controller, *args, **kwargs)
        controller._worker_target = instrumented_worker
    sidecar = output.with_suffix('.worker.json')
    if sidecar.exists():
        raise FileExistsError(sidecar)
    os.environ['PY_ELK_E10_SIDECAR'] = str(sidecar)
    ExecutionController.__init__ = constructor
    try:
        observed = await public.sample(wheel, request)
    finally:
        ExecutionController.__init__ = original
        os.environ.pop('PY_ELK_E10_SIDECAR', None)
    observed['mode'] = 'instrumented'
    observed['executionDependencies']['tools/platform/instrument_e10.py'] = public.sha(__file__)
    raw = sidecar.read_bytes(); worker = json.loads(raw)
    if worker['pid'] != observed['worker']['pid'] or any('finishNs' not in item for item in worker['spans']):
        raise ValueError('Incomplete or unrelated worker sidecar')
    return {'schema': 'py-elk-e10-instrumented-observation/v1', 'mode': 'instrumented',
            'observation': observed, 'workerBytesBase64': base64.b64encode(raw).decode(),
            'workerSha256': hashlib.sha256(raw).hexdigest(), 'fullValidation': False,
            'limitations': ['Private monitor hooks add overhead; excluded from all public throughput statistics.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    load_benchmark().save(args.out, asyncio.run(sample(args.wheel.absolute(), args.request.absolute(), args.out.absolute())))


if __name__ == '__main__':
    main()
