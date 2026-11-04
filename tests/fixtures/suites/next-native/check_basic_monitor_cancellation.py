"""PRIVATE_SRC NEW_REPORT; only source BasicProgressMonitor constant contract."""
import hashlib,json,sys
from pathlib import Path
source,out=map(Path,sys.argv[1:3]);sys.path.insert(0,str(source.resolve()))
from pyelk.execution.diagnostics import BasicProgressMonitor
monitor=BasicProgressMonitor();assert monitor.is_canceled()is False
monitor.begin('parent',1);child=monitor.sub_task(1)
assert monitor.is_canceled()is False and child.is_canceled()is False
child.begin('child',1);child.done();monitor.done()
assert monitor.is_canceled()is False and child.is_canceled()is False
with out.open('x',encoding='utf-8')as f:json.dump({'passed':True,'scope':'source BasicProgressMonitor isCanceled constant before/during/after tasks, independent of public OS cancellation/timeout',
 'sourceFileSha256':hashlib.sha256((source/'pyelk/execution/diagnostics.py').read_bytes()).hexdigest(),
 'wholeMonitorOrLayoutReexecuted':False,'fullValidation':False},f,indent=2)
