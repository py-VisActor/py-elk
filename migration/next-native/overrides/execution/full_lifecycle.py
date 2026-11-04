"""Native FIFO scheduling with a persistent registry/provider worker.

Cancellation, deadlines and close terminate the real process. A successful job
releases its lease while the worker remains idle for provider/state reuse.
"""
import builtins
import multiprocessing
import time

from .._errors import ResourceClosedError,WorkerExecutionError
from .full_worker import worker_main
from .lifecycle import ExecutionController
from .wire_codec import encode_json_tree,decode_json_tree


class FullExecutionController(ExecutionController):
    def __init__(self,constructor=None,*,max_pending=16,timeout=None):
        super().__init__(constructor,max_pending=max_pending,timeout=timeout)
        self._runtime_process=None
        self._runtime_connection=None
        self._retired_pids=set()
        self._worker_target=worker_main

    def _job_snapshot(self,job):
        value=super()._job_snapshot(job)
        value['lease_released']=value['reaped']
        value['reaped']=job.pid is None or job.pid in self._retired_pids
        return value

    def snapshot(self):
        value=super().snapshot()
        with self._reap_lock:
            process=self._runtime_process
            try:alive=process is not None and process.is_alive()
            except(ValueError,AssertionError):alive=False
            value['worker_pid']=process.pid if alive else None
        value['worker_alive']=alive
        value['worker_persistent']=True
        for job in value['jobs']:
            job['reaped']=job['pid']is None or job['pid']in self._retired_pids
        return value

    def _drop_runtime_locked(self):
        process=self._runtime_process;connection=self._runtime_connection
        if process is None:return None
        pid=process.pid
        try:
            if process.is_alive():process.terminate()
            process.join(0.5)
            if process.is_alive():process.kill();process.join(2)
            if process.is_alive():
                raise WorkerExecutionError('WORKER_SHUTDOWN_FAILED','','The native worker remains alive')
            exitcode=process.exitcode
            if pid is not None:self._retired_pids.add(pid)
            process.close()
            self._runtime_process=None;self._runtime_connection=None
            return exitcode
        finally:
            if self._runtime_process is None and connection is not None:connection.close()

    def _drop_runtime(self):
        with self._reap_lock:return self._drop_runtime_locked()

    def _ensure_runtime(self):
        with self._reap_lock:
            with self._lock:
                if self._state!='open':
                    raise ResourceClosedError('RESOURCE_CLOSED','','The native instance is closed')
            if self._runtime_process is not None:
                if self._runtime_process.is_alive():
                    return self._runtime_process,self._runtime_connection
                self._drop_runtime_locked()
            context=multiprocessing.get_context('spawn')
            parent,child=context.Pipe(duplex=True)
            process=context.Process(target=self._worker_target,args=(child,encode_json_tree(self._constructor)),
                                    name='pyelk-runtime',daemon=True)
            try:process.start()
            except BaseException:
                parent.close();child.close();process.close();raise
            child.close()
            self._runtime_process=process;self._runtime_connection=parent
            return process,parent

    def _reap(self,job,*,stop):
        if job.process is self._runtime_process and job.process is not None:
            job.exitcode=self._drop_runtime()
            job.reaped=True
        else:
            super()._reap(job,stop=stop)

    @staticmethod
    def _decode(job,envelope):
        if type(envelope)is dict and envelope.get('kind')=='result':
            expected={'kind','job_id','graph_tokens','trace','pid','process_time'}
            if set(envelope)!=expected or type(envelope['graph_tokens'])is not list:
                raise WorkerExecutionError('WORKER_PROTOCOL_ERROR','','Invalid native result envelope')
            try:graph=decode_json_tree(envelope['graph_tokens'])
            except(ValueError,TypeError)as error:
                raise WorkerExecutionError('WORKER_PROTOCOL_ERROR','','Invalid native result tree')from error
            envelope={key:value for key,value in envelope.items()if key!='graph_tokens'}
            envelope['graph']=graph
        if type(envelope)is dict and envelope.get('kind')=='error'and envelope.get('category')=='execution':
            from .. import _errors
            expected={'kind','job_id','category','type','code','path','message'}
            if(set(envelope)!=expected or type(envelope['job_id'])is not int
               or envelope['job_id']!=job.job_id
               or any(type(envelope[k])is not str for k in('type','code','path','message'))):
                raise WorkerExecutionError('WORKER_PROTOCOL_ERROR','','Invalid execution error envelope')
            error_type=getattr(_errors,envelope['type'],None)
            if not isinstance(error_type,type)or not issubclass(error_type,_errors.ExecutionError):
                raise WorkerExecutionError('WORKER_PROTOCOL_ERROR','','Unknown execution error type')
            return'error',error_type(envelope['code'],envelope['path'],envelope['message'])
        if type(envelope)is dict and envelope.get('kind')=='error'and envelope.get('category')=='algorithm':
            expected={'kind','job_id','category','type','code','path','message'}
            if(set(envelope)!=expected or type(envelope['job_id'])is not int
               or envelope['job_id']!=job.job_id
               or any(type(envelope[k])is not str for k in('type','code','path','message'))
               or envelope['code']!='WORKER_EXECUTION_FAILED'or envelope['path']!=''):
                raise WorkerExecutionError('WORKER_PROTOCOL_ERROR','','Invalid algorithm error envelope')
            error_type=getattr(builtins,envelope['type'],None)
            if error_type in(TypeError,ValueError,ReferenceError,RuntimeError,IndexError,
                              KeyError,OverflowError,ArithmeticError,RecursionError):
                return'error',error_type(envelope['message'])
            return'error',WorkerExecutionError(envelope['code'],envelope['path'],envelope['message'])
        return ExecutionController._decode(job,envelope)

    def _run(self,job):
        result=error=None;reason=self._stop_reason(job);fatal=False;lease_complete=True
        try:
            if reason is None:
                process,connection=self._ensure_runtime()
                with self._lock:
                    job.process=process;job.connection=connection;job.pid=process.pid
                    job.started_at=time.monotonic();job.state='running'
                reason=self._stop_reason(job)
                if reason is None:
                    connection.send({'job_id':job.job_id,'graph_tokens':encode_json_tree(job.graph),
                                     'argument_tokens':encode_json_tree(job.arguments)})
                    while True:
                        self._sweep_queue();reason=self._stop_reason(job)
                        if reason is not None:break
                        if connection.poll(0.005):
                            kind,value=self._decode(job,connection.recv())
                            if kind=='progress':
                                with self._lock:job.progress=value
                                continue
                            if kind=='result':result=value
                            else:error=value
                            break
                        if process.exitcode is not None:
                            raise WorkerExecutionError('WORKER_EXITED','','Native worker exited without a result')
        except(EOFError,BrokenPipeError,OSError)as caught:
            fatal=True;error=WorkerExecutionError('WORKER_EXITED','',str(caught))
        except Exception as caught:
            fatal=True;error=caught if isinstance(caught,(WorkerExecutionError,ResourceClosedError))else WorkerExecutionError(
                'WORKER_START_FAILED'if job.started_at is None else'WORKER_EXECUTION_FAILED','',str(caught))
        finally:
            reason=self._stop_reason(job)or reason
            if reason is not None or fatal:
                try:
                    if job.process is not None:self._reap(job,stop=True)
                except Exception as caught:
                    error=caught;lease_complete=False
            # Internal reaped is the inherited scheduler's lease-complete flag.
            # Public snapshots distinguish it from the real process reap state.
            job.reaped=lease_complete
        with self._lock:
            reason=self._stop_reason(job)or reason
            if reason is not None:result,error=None,self._reason_error(reason)
            if not lease_complete:
                self._state='closing';reason=None
                error=WorkerExecutionError('WORKER_SHUTDOWN_FAILED','','The native worker could not be reaped')
            state='cancelled'if reason=='cancel'else'failed'if error is not None else'returned'
            self._finish(job,state,result,error)

    def close(self):
        try:super().close()
        finally:self._drop_runtime()
