"""Syntax/import checks only; never execute a graph, provider or layout.

Use an explicit source directory so private migration and promoted package
checks cannot accidentally import another installed copy of pyelk.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    source=args.source_dir.resolve();package=source/'pyelk'
    if not package.is_dir():parser.error('source-dir must contain pyelk')
    if args.out.exists():parser.error('out already exists; use a new report path')
    if any(name=='pyelk'or name.startswith('pyelk.')for name in sys.modules):
        parser.error('run in a fresh interpreter without a previously imported pyelk')
    started=time.monotonic();failures=[];files={};modules=[]
    for path in sorted(package.rglob('*.py')):
        name=path.relative_to(source).as_posix();raw=path.read_bytes()
        files[name]=hashlib.sha256(raw).hexdigest()
        try:ast.parse(raw,filename=str(path))
        except(SyntaxError,ValueError)as error:
            failures.append({'stage':'syntax','file':name,'error':str(error)})
        module=name[:-3].replace('/','.')
        if module.endswith('.__init__'):module=module[:-9]
        modules.append(module)
    sys.path.insert(0,str(source))
    if not failures:
        for module in modules:
            try:
                loaded=importlib.import_module(module)
                Path(loaded.__file__).resolve().relative_to(package)
            except Exception as error:
                failures.append({'stage':'import','module':module,
                                 'type':type(error).__name__,'error':str(error)})
    report={'schema':'py-elk-implementation-interfaces/v1','passed':not failures,
            'sourceDirectory':str(source),'pythonModules':len(files),
            'sourceFilesSha256':files,'failures':failures,
            'elapsedSeconds':time.monotonic()-started,
            'layoutExecutions':0,'referenceExecutions':0,'differentialChecks':0,
            'correctnessVerified':False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key]for key in('passed','pythonModules','failures','elapsedSeconds')},
                     ensure_ascii=True))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
