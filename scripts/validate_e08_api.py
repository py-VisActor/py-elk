"""Independent pinned E08 reference facts and explicit native host mapping.

Reference queries retain the full official catalog. They do not certify that
the native bounded implementation implements those algorithms or options.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import sys
import time

# Trusted development tooling remains importable under -I. Never add src;
# candidate pyelk must resolve from the independently verified installation.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from layout_checks import ROOT, contained, diff, geometry, load, sha256, write
from validate_layout import run
from validate_e04_runtime import embedded_json

SUITE = "tests/fixtures/suites/E08-api"
RECORD = "references/e08-api-validation.json"
COLLECTOR = "tools/reference/capture_e08_api.cjs"
CASE_COUNT = 44
REPEAT = 3
NATIVE_REQUEST = SUITE+"/native-request.json"
NATIVE_REQUEST_SHA = "ec027476a833dd6bd89affb777a0d47f6651aeecf145349df1d8c4702cb35fa9"
NATIVE_SCHEMA = "references/e08-metadata-schema.json"
NATIVE_SCHEMA_SHA = "4d258ec6fb90c1a7a72a26ec300b2d9177de20c16a0dd961ebacc69e845444e3"
LIFECYCLE_HELPER = "tests/conformance/test_e08_api_lifecycle.py"
NATIVE_PROCESSORS = ("EdgeAndLayerConstraintEdgeReverser","GreedyCycleBreaker","LayerConstraintPreprocessor",
    "NetworkSimplexLayerer","LayerConstraintPostprocessor","LongEdgeSplitter","PortSideProcessor","PortListSorter",
    "LayerSweepCrossingMinimizer","LayerSweepCrossingMinimizer","InLayerConstraintProcessor","LabelAndNodeSizeProcessor",
    "InnermostNodeMarginCalculator","BKNodePlacer","LayerSizeAndGraphHeightCalculator","OrthogonalEdgeRouter",
    "LongEdgeJoiner","EndLabelSorter","ReversedEdgeRestorer")
CASES_SHA = "b575bb717d5183da1ca533d73eb262eebeb7ecdd797c1a9c8c74f7864ae1188a"
METHODS = {"knownLayoutAlgorithms":"algorithms", "knownLayoutOptions":"options", "knownLayoutCategories":"categories"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal(a, b, message):
    require(diff(a, b)["passed"], message)


def finite_number(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False


def original_path(value):
    require(type(value) is str and bool(value), "Missing original process path")
    result=PureWindowsPath(value) if PureWindowsPath(value).drive else PurePosixPath(value)
    require(result.is_absolute(), "Original process path must be absolute")
    return result


def reference_value(actual, expected, measured):
    """Only exact, frozen official logging-clock leaves vary between captures.

    This reference-only fact check never changes the layout comparator profile.
    Raw clocks remain recorded. Business fields and coordinates remain exact.
    """
    value=copy.deepcopy(actual)
    for path in measured:
        require(path[0]=="logging" and path[-1]=="executionTime", "Unapproved reference clock field")
        target,source=value,expected
        for part in path[:-1]:target,source=target[part],source[part]
        seconds=target[path[-1]]
        require(finite_number(seconds) and seconds>=0,"Invalid measured reference logging duration")
        target[path[-1]]=source[path[-1]]
    equal(value,expected,"Reference complete layout result/input/argument fields differ")


def definitions(root=ROOT):
    root=Path(root);path=root/SUITE/"cases.json";value=load(path)
    require(sha256(path)==CASES_SHA, "Fixed independently observed API definitions changed")
    require(value["schema"]=="py-elk-e08-api-cases/v1" and type(value["caseCount"]) is int and value["caseCount"]==CASE_COUNT and
            type(value["repeat"]) is int and value["repeat"]==REPEAT and len(value["cases"])==CASE_COUNT,
            "API definition/repetition denominator differs")
    require(len({c["id"] for c in value["cases"]})==CASE_COUNT,"Duplicate API definition")
    for case in value["cases"]:
        request=load(contained(root/SUITE,case["request"]))
        require(sha256(contained(root/SUITE,case["request"]))==case["requestSha256"],"Fixed original API request bytes changed")
        require(request["schema"]=="py-elk-e08-api-request/v1" and request["id"]==case["id"] and bool(request["steps"]),"API request identity differs")
        require(type(case["expectedProcessExit"]) is int and case["expectedProcessExit"] in (0,1),"Unknown reference process outcome")
    return value


def reference_sources(root=ROOT):
    root=Path(root)
    names=[COLLECTOR,SUITE+"/cases.json",*["references/metadata/"+kind+".json" for kind in METHODS.values()]]
    names.extend(SUITE+"/"+case["request"] for case in definitions(root)["cases"])
    return {name:sha256(root/name) for name in names}


def baseline_identity(lock):
    """Immutable upstream identity, excluding current Python evidence/status."""
    return {"javascript":{k:lock["javascript"][k] for k in
            ("repository","npmPackage","version","tag","commit","licenseSpdx")},
            "distribution":copy.deepcopy(lock["distribution"]),"sourceSha256":copy.deepcopy(lock["sourceSha256"])}


def validate_metadata_result(actual, expected_ids, method, root=ROOT, registry=()):
    require(type(actual) is list and [r.get("id") for r in actual]==expected_ids,"Reference metadata ID order/denominator differs")
    catalog={r["id"]:r for r in load(Path(root)/"references/metadata"/(METHODS[method]+".json"))}
    expected=[]
    for identity in expected_ids:
        require(identity in catalog,"Reference metadata contains unknown ID")
        value=copy.deepcopy(catalog[identity])
        if method=="knownLayoutCategories" and "knownLayouters" in value:
            value["knownLayouters"]=[v for v in value["knownLayouters"] if v in registry]
            if not value["knownLayouters"]:value.pop("knownLayouters")
        expected.append(value)
    equal(actual,expected,"Reference metadata fields differ from pinned complete catalog")


def validate_reference_events(case, request, events, root=ROOT):
    expected=case["expectedEvents"]
    require(type(events) is list and len(events)==len(expected) and bool(events),"Reference event denominator differs")
    registry=[]
    catalog_algorithms=load(Path(root)/"references/metadata/algorithms.json")
    selectors={v["id"].removeprefix("org.eclipse.elk."):v["id"] for v in catalog_algorithms}
    for ordinal,(event,wanted) in enumerate(zip(events,expected)):
        for field in ("kind","id","outcome"):
            equal(event.get(field),wanted[field],"Reference event identity/outcome differs")
        equal(event.get("operation"),wanted["operation"],"Reference operation order differs")
        if event["outcome"]=="instanceNotConstructed":
            require("returnKind" not in event,"Unconstructed instance cannot provide a call return style")
        elif "returnKind" in wanted:
            equal(event.get("returnKind"),wanted["returnKind"],"Reference synchronous/Promise error style differs")
        if "optionsAfter" in wanted:
            equal({"present":"optionsAfter" in event,"value":event.get("optionsAfter")},wanted["optionsAfter"],"Reference constructor input side effects differ")
        if "values" in wanted:
            require(set(wanted["values"])=={k for k in ("result","graphAfter","argumentsAfter") if k in event},"Reference API data field denominator differs")
            for name,value in wanted["values"].items():
                reference_value(event[name],value,wanted["measuredFields"].get(name,[]))
        if event["kind"]=="constructor" and event["outcome"]=="returned":
            options=request["steps"][ordinal].get("constructor",{})
            selection=options.get("algorithms") if type(options) is dict and "algorithms" in options else list(selectors)
            selected=selection if type(selection) is list else []
            for identity in ["org.eclipse.elk.fixed","org.eclipse.elk.box","org.eclipse.elk.random",*[selectors[v] for v in selected if type(v) is str and v in selectors]]:
                if identity not in registry:registry.append(identity)
        if wanted["outcome"]=="threw":
            equal({k:event["error"][k] for k in ("name","message")},wanted["error"],"Reference public error name/message differs")
        method=event.get("operation")
        if "metadataIds" in wanted:
            method=event.get("method") if method=="mutate-query" else method
            require(method in METHODS,"Unknown metadata query")
            validate_metadata_result(event["result"],wanted["metadataIds"],method,root,registry)
            if method=="knownLayoutAlgorithms":registry=list(wanted["metadataIds"])
            if method=="knownLayoutCategories":
                catalog=load(Path(root)/"references/metadata/categories.json")
                expected_categories=copy.deepcopy(catalog)
                for category in expected_categories:
                    if "knownLayouters" in category:
                        category["knownLayouters"]=[v for v in category["knownLayouters"] if v in registry]
                        if not category["knownLayouters"]:category.pop("knownLayouters")
                equal(event["result"],expected_categories,"Reference category registration links differ")
            if event.get("operation")=="mutate-query":
                require(event["sameArray"] is False,"Query reused caller-mutated array")
                equal(event["before"],event["result"],"Caller metadata mutation leaked into next query")
        if method=="layout" and event["outcome"]=="returned":
            require(type(event["result"]) is dict and event["returnKind"]=="Promise","Reference layout return contract differs")
            equal(event["result"],event["graphAfter"],"Reference result and same mutated FakeWorker graph differ")
        # The collector clones each step's graph immediately before invoking it.
        if event["kind"]=="call" and event["outcome"] not in ("instanceNotConstructed",) and event.get("operation")!="mutate-query":
            require(ordinal<len(request["steps"]),"Reference step binding differs")


def verify_reference(directory, root=ROOT):
    root=Path(root);directory=Path(directory).resolve();index=load(directory/"index.json")
    require(index["schema"]=="py-elk-e08-api-reference/v3","Unknown reference index")
    require(type(index["caseCount"]) is int and index["caseCount"]==CASE_COUNT and type(index["repeat"]) is int and index["repeat"]==REPEAT and
            type(index["actualProcesses"]) is int and index["actualProcesses"]==CASE_COUNT*REPEAT,"Reference process denominator differs")
    equal(index["sourceSha256"],reference_sources(root),"Current reference inputs/collector/catalog bytes differ")
    cases=definitions(root)["cases"];equal([c["id"] for c in index["cases"]],[c["id"] for c in cases],"Reference case order differs")
    files={p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file() and p!=directory/"index.json"}
    require(files==set(index["filesSha256"]),"Raw reference file denominator differs")
    for name,fingerprint in index["filesSha256"].items():
        require(sha256(contained(directory,name))==fingerprint,"Raw reference bytes differ: "+name)
    lock=load(root/"UPSTREAM.json");equal(index["baseline"],baseline_identity(lock),"Reference package baseline differs")
    equal(baseline_identity(load(directory/"source-lock.json")),index["baseline"],"Original source lock baseline differs")
    origin=original_path(index["actualExecutionRoot"])
    source_root=original_path(index["actualSourceRoot"])
    require(index["workingDirectory"]==str(source_root),"Original reference working directory differs")
    for definition,row in zip(cases,index["cases"]):
        request_path=contained(directory,row["request"]);original=contained(root/SUITE,definition["request"])
        require(request_path.read_bytes()==original.read_bytes() and sha256(request_path)==row["requestSha256"],"Reference original request bytes differ")
        request=load(request_path);require(len(row["captures"])==REPEAT,"Missing independent API repetitions")
        for repetition,capture in enumerate(row["captures"]):
            require(type(capture["repetition"]) is int and capture["repetition"]==repetition,"Reference repetition slot differs")
            relative="observations/"+row["id"]+"/repeat-"+str(repetition)
            require(capture["directory"]==relative,"Reference capture slot differs")
            folder=contained(directory,relative+"/command.json").parent;command=load(folder/"command.json")
            expected_argv=[index["node"],str(source_root/COLLECTOR),index["package"],str(origin/row["request"]),str(origin/relative/"observation.json")]
            require(command["argv"]==expected_argv and command["cwd"]==index["workingDirectory"] and type(command["exitCode"]) is int and
                    command["exitCode"]==definition["expectedProcessExit"] and command["timedOut"] is False,"Actual reference argv/exit/isolation differs")
            for stream in ("stdout","stderr"):
                require(sha256(folder/(stream+".log"))==command[stream+"Sha256"],"Reference actual process logs differ")
            identity=load(folder/"observation.json.identity.json")
            require(identity["schema"]=="py-elk-e08-api-observation/v1" and identity["id"]==row["id"] and identity["requestSha256"]==row["requestSha256"],"Reference identity binding differs")
            engine=identity["engine"];entry=request.get("entrypoint","lib/elk.bundled.js")
            require(engine["name"]=="elkjs" and engine["version"]==lock["javascript"]["version"] and engine["entrypoint"]==entry and
                    engine["entrypointSha256"]==lock["distribution"]["sha256Files"][entry] and engine["node"]==index["nodeVersion"],"Reference engine identity differs")
            events=[embedded_json(line.encode('utf-8')) for line in (folder/"observation.json.events.jsonl").read_text(encoding="utf-8").splitlines()]
            validate_reference_events(definition,request,events,root)
            if definition["expectedProcessExit"]==0:
                observation=load(folder/"observation.json")
                equal({k:observation[k] for k in identity},identity,"Reference full observation identity differs")
                equal(observation["events"],events,"Reference event stream differs")
            else:
                require(not (folder/"observation.json").exists() and definition["expectedCrash"] in (folder/"stderr.log").read_text(encoding="utf-8"),"Expected asynchronous worker crash evidence differs")
    return {"status":"E08_REFERENCE_API_FACTS_VALIDATED","passed":True,"caseCount":CASE_COUNT,"repeat":REPEAT,
            "actualProcesses":CASE_COUNT*REPEAT,"expectedWorkerCrashProcesses":9,"pythonAlgorithmsVerified":0,
            "runtimeReexecuted":False,"historicalExecutionAuthenticated":False}


def capture_reference(out, package, node="node", root=ROOT):
    root=Path(root);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(root/"UPSTREAM.json",out/"source-lock.json")
    node=str(Path(shutil.which(str(node)) or str(node)).resolve());package=str(Path(package).resolve())
    rows=[];request_dir=out/"requests";request_dir.mkdir()
    for case in definitions(root)["cases"]:
        target=request_dir/(case["id"]+".json");shutil.copyfile(contained(root/SUITE,case["request"]),target)
        row={"id":case["id"],"request":target.relative_to(out).as_posix(),"requestSha256":sha256(target),"captures":[]}
        for repetition in range(REPEAT):
            folder=out/"observations"/case["id"]/("repeat-"+str(repetition));folder.mkdir(parents=True)
            command=run([node,str(root/COLLECTOR),package,str(target),str(folder/"observation.json")],folder,20)
            require(type(command["exitCode"]) is int and command["exitCode"]==case["expectedProcessExit"] and command["timedOut"] is False,"Unexpected actual reference failure: "+case["id"])
            row["captures"].append({"repetition":repetition,"directory":folder.relative_to(out).as_posix()})
        rows.append(row);print("Captured",case["id"],flush=True)
    lock=load(root/"UPSTREAM.json")
    node_version=load(out/rows[0]["captures"][0]["directory"]/"observation.json.identity.json")["engine"]["node"]
    index={"schema":"py-elk-e08-api-reference/v3","caseCount":CASE_COUNT,"repeat":REPEAT,"actualProcesses":CASE_COUNT*REPEAT,
           "actualSourceRoot":str(root),"workingDirectory":str(root),
           "actualExecutionRoot":str(out),"node":node,"nodeVersion":node_version,"nodeSha256":sha256(Path(node)),"package":package,
           "baseline":baseline_identity(lock),
           "sourceSha256":reference_sources(root),"cases":rows,
           "filesSha256":{p.relative_to(out).as_posix():sha256(p) for p in sorted(out.rglob("*")) if p.is_file()}}
    write(out/"index.json",index)
    return verify_reference(out,root)


def check(root=ROOT):
    root=Path(root)
    try:
        record=load(root/RECORD)
        require(record["schema"]=="py-elk-e08-api-validation/v1","Unknown API validation record")
        result=verify_reference(root/SUITE/"oracle",root)
        require(record["referenceIndexSha256"]==sha256(root/SUITE/"oracle/index.json"),"Reference validation record differs")
        require(record['nativeRuntimeVerified'] is False and type(record['pythonAlgorithmsVerified']) is int and record['pythonAlgorithmsVerified']==0 and
                record['packagePublished'] is False and len(record['explicitHostDifferences'])==8,'Reference facts were promoted or host differences hidden')
        equal(record["sourceSha256"],reference_sources(root),"Reference source record differs")
        host=load(root/"references/e08-host-contract.json")
        require(host["id"]=="E08-ADR0007-revision1","Explicit native contract ID differs")
        equal(host['registration'],{"default":["layered"],"empty":[],"aliases":["layered","org.eclipse.elk.layered"],"instanceIsolated":True,"optionCount":9},"Explicit native registration mapping differs")
        require(host["loggingTrueSupported"] is False and host["measureExecutionTimeTrueSupported"] is False and
                type(host["pythonAlgorithmsVerified"]) is int and host["pythonAlgorithmsVerified"]==0 and host["packagePublished"] is False,"Native host facts promoted beyond acceptance")
        return {**result,"status":"E08_API_REFERENCE_AND_HOST_CONTRACT_VALIDATED","nativeRuntimeVerified":False}
    except (ValueError,OSError,KeyError,TypeError,IndexError) as e:
        return {"status":"FAIL","passed":False,"errors":[str(e)],"nativeRuntimeVerified":False,"pythonAlgorithmsVerified":0}


def native_metadata_contract(root=ROOT):
    root=Path(root)
    e09 = (root/"references/e09-host-contract.json").is_file()
    require(sha256(root/NATIVE_SCHEMA)==NATIVE_SCHEMA_SHA,"Frozen native metadata contract changed")
    expected=load(root/("references/e09-metadata-schema.json" if e09 else NATIVE_SCHEMA))["expectedQueries"]
    options=expected["default"]["options"]
    specs={"algorithm":("algorithm",None),"direction":("enum","UNDEFINED"),"edgeRouting":("enum","ORTHOGONAL"),
           "padding":("padding",{"top":12,"right":12,"bottom":12,"left":12}),"randomSeed":("seed",1),
           "separateConnectedComponents":("boolean",True),"spacing.componentComponent":("spacing",20),
           "spacing.nodeNode":("spacing",20),"layered.spacing.nodeNodeBetweenLayers":("spacing",20)}
    catalog=load(root/"references/metadata/options.json")
    ids={"org.eclipse.elk."+key for key in specs}
    equal([v["id"] for v in options],[v["id"] for v in catalog if v["id"] in ids],"Native nine-option source order differs")
    by_id={v["id"]:v for v in catalog}
    for option in options:
        equal({k:v for k,v in option.items() if k!="native"},by_id[option["id"]],"Native option reference fields changed")
        kind,default=specs[option["id"].removeprefix("org.eclipse.elk.")]
        equal([option["native"]["valueType"],option["native"]["defaultValue"]],[kind,default],"Native option declared parser default differs")
    algorithms=expected["default"]["algorithms"]
    require(len(algorithms)==1 and algorithms[0]["id"]=="org.eclipse.elk.layered","Native unimplemented algorithm advertised")
    original=next(v for v in load(root/"references/metadata/algorithms.json") if v["id"]=="org.eclipse.elk.layered")
    equal(algorithms[0]["knownOptions"],[v for v in original["knownOptions"] if v in ids],"Native algorithm option applicability differs")
    equal(algorithms[0]["supportedFeatures"],["SELF_LOOPS","MULTI_EDGES"],"Native unsupported feature advertised")
    constraints=algorithms[0]["native"]["constraints"]
    equal(constraints["originalChildNodes"],{"minimum":0,"maximum":8},"Native node bound differs")
    equal(constraints["originalEdges"],{"minimum":0,"maximum":28},"Native edge bound differs")
    require(all(constraints[k] is False for k in ("ports","labels","compound")),"Native geometric scope expanded")
    require(all(constraints[k] is e09 for k in ("logging","measureExecutionTime")),"Native diagnostics scope differs")
    category=next(v for v in load(root/"references/metadata/categories.json") if v["id"]=="org.eclipse.elk.layered")
    equal(expected["default"]["categories"],[category],"Native category fields differ")
    equal(expected["algorithmsEmpty"],{"algorithms":[],"options":options,"categories":[]},"Empty native registry differs")
    return expected


def native_sources(root=ROOT):
    root=Path(root)
    names = ["scripts/validate_e08_api.py",LIFECYCLE_HELPER,NATIVE_REQUEST,NATIVE_SCHEMA,"references/e08-host-contract.json"]
    if (root/"references/e09-host-contract.json").is_file():
        names += ["references/e09-host-contract.json", "references/e09-metadata-schema.json"]
    return {name:sha256(root/name) for name in names}


def native_helper(root=ROOT):
    spec=importlib.util.spec_from_file_location("e08_independent_runtime_probe",Path(root)/LIFECYCLE_HELPER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def candidate_capture(request_path,out):
    require(sys.flags.isolated==1 and os.environ.get("PATH")=="" and
            all(name not in os.environ for name in ("PYTHONPATH","PYTHONHOME","NODE_OPTIONS","NODE_PATH")),"Installed candidate must use -I/empty PATH/no overrides")
    require(Path(request_path).read_bytes()==(ROOT/NATIVE_REQUEST).read_bytes() and sha256(Path(request_path))==NATIVE_REQUEST_SHA,"Native original request differs")
    import pyelk
    module=Path(pyelk.__file__).resolve().parent
    require(not module.is_relative_to(ROOT/"src"),"Installed capture imported source tree")
    files={p.relative_to(module).as_posix():sha256(p) for p in sorted(module.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    helper=native_helper()
    started=time.monotonic()
    lifecycle=asyncio.run(helper.capture_lifecycle(pyelk.ELK,load(Path(request_path))))
    value={"schema":"py-elk-e08-native-observation/v2","requestSha256":NATIVE_REQUEST_SHA,
           "captureInterval":{"clock":"time.monotonic","started":started,"finished":time.monotonic()},
           "engine":{"name":"pyelk","version":pyelk.__version__,"modulePath":str(module),"python":sys.version,
                     "executable":sys.executable,"isolated":True,"pid":os.getpid(),"parentPid":os.getppid(),"packageFilesSha256":files},
           "sourceSha256":native_sources(),"lifecycle":lifecycle}
    write(Path(out),value)
    return {"status":"E08_NATIVE_CAPTURE_RECORDED","passed":True}


def _idle(snapshot, *, closed=False):
    require(type(snapshot["pending"]) is int and snapshot["pending"]==0 and snapshot["running"] is None and snapshot["queued"]==[] and
            snapshot["worker_pid"] is None and snapshot["worker_alive"] is False and snapshot["dispatcher_alive"] is False,
            "Native worker/queue/thread was not released")
    if closed:require(snapshot["state"]=="closed","Native close state differs")


def _os_pid(record, alive):
    require(type(record["pid"]) is int and record["pid"]>0 and record["alive"] is alive,"Actual OS PID observation differs")
    if record["method"]=="OpenProcess/GetExitCodeProcess":
        if record["opened"] is True:
            require(type(record["exitCode"]) is int and (record["exitCode"]==259)==alive,"OS exit-code observation differs")
        else:require(not alive and record["error"] in (87,1168),"OS PID lookup did not prove absence")
    else:
        require(record["method"]=="kill(pid,0)" and record["error"]==(None if alive else "ESRCH"),"Unknown OS PID proof")


def native_error(actual, name, code, path, message):
    equal(actual,{'type':name,'code':code,'path':path,'message':message},'Native public error name/code/path/message differs')


def validate_snapshot(snapshot, interval):
    """Typed diagnostics at explicit native protocol positions only.

    A popped queued job may be in spawn startup before becoming running. A
    running snapshot may observe reaping just before terminal publication.
    Failed/cancelled exit0 is legal when cancellation wins after computation.
    """
    require(set(snapshot)=={'state','pending','queued','running','worker_pid','worker_alive','dispatcher_alive','last_submitted_id','jobs'},'Native snapshot field denominator differs')
    require(snapshot['state'] in ('new','open','closing','closed') and type(snapshot['pending']) is int and snapshot['pending']>=0 and
            type(snapshot['last_submitted_id']) is int and snapshot['last_submitted_id']>=0 and
            type(snapshot['worker_alive']) is bool and type(snapshot['dispatcher_alive']) is bool,'Invalid native snapshot state/count types')
    jobs=snapshot['jobs'];require(type(jobs) is list,'Native snapshot jobs must be a list')
    ids=[];active=[]
    for job in jobs:
        require(set(job)=={'job_id','state','pid','exitcode','reaped','submitted_at','started_at','finished_at','progress'},'Native job field denominator differs')
        require(type(job['job_id']) is int and 0<job['job_id']<=snapshot['last_submitted_id'],'Native job ID must be an integer')
        ids.append(job['job_id'])
        require(job['state'] in ('queued','running','returned','failed','cancelled') and type(job['reaped']) is bool,'Invalid native job state/reap type')
        pid=job['pid'];require(pid is None or type(pid) is int and pid>0,'Invalid native job PID')
        require(job['exitcode'] is None or type(job['exitcode']) is int,'Native process exit status must be an integer')
        stamps=[job[k] for k in ('submitted_at','started_at','finished_at') if job[k] is not None]
        require(job['submitted_at'] is not None and all(finite_number(v) and interval['started']<=v<=interval['finished'] for v in stamps) and stamps==sorted(stamps),
                'Native job lifecycle clocks contradict capture interval/order')
        if job['state'] in ('queued','running'):active.append(job)
        else:
            require(job['reaped'] is True and job['finished_at'] is not None,'Terminal native job was not fully reaped')
            if pid is None:require(job['started_at'] is None and job['exitcode'] is None,'Unspawned native job has process exit/start fields')
            else:require(job['started_at'] is not None and type(job['exitcode']) is int,'Spawned terminal job lacks actual process exit/start')
        if job['state']=='returned':
            require(type(pid) is int and job['started_at'] is not None and type(job['exitcode']) is int and job['exitcode']==0 and job['reaped'] is True,
                    'Returned native job lacks successful integer exit0/reap')
        if job['state']=='queued':require(pid is None and job['started_at'] is None,'Queued native job already started a process')
        if job['state']=='running':require(type(pid) is int and job['started_at'] is not None and job['finished_at'] is None,'Running native job lacks actual process start')
        progress=job['progress']
        if progress is not None:
            require(set(progress)=={'index','processor','previous_processor','previous_outcome','process_time'},'Native phase progress field denominator differs')
            index=progress['index']
            require(type(index) is int and 0<=index<len(NATIVE_PROCESSORS) and progress['processor']==NATIVE_PROCESSORS[index] and
                    progress['previous_processor']==(None if index==0 else NATIVE_PROCESSORS[index-1]) and progress['previous_outcome']==(None if index==0 else 'returned') and
                    finite_number(progress['process_time']) and progress['process_time']>=0,'Native phase/CPU progress differs from original DAG request path')
        if job['state']=='returned':require(progress is not None and progress['index']==len(NATIVE_PROCESSORS)-1,'Returned original nonempty DAG lacks complete processor sequence')
    require(ids==sorted(ids) and len(set(ids))==len(ids),'Native snapshot job identities duplicated/reordered')
    require(snapshot['pending']==len(active),'Native snapshot pending denominator differs')
    queued=snapshot['queued'];require(type(queued) is list and all(type(v) is int for v in queued) and queued==sorted(set(queued)),'Invalid native FIFO queue IDs')
    require(set(queued)<={j['job_id'] for j in active if j['state']=='queued'},'Native queue/state identity differs')
    running=snapshot['running']
    require(sum(j['state']=='running' for j in active)<=1,'Native instance has multiple running worker slots')
    starting={j['job_id'] for j in active if j['state']=='queued'}-set(queued)
    require(len(starting)<=(1 if running is None else 0),'Native instance has multiple unqueued startup slots')
    if running is not None:
        require(type(running) is int and any(j['job_id']==running and j['state']=='running' and j['pid']==snapshot['worker_pid'] for j in active),
                'Native running-slot identity differs')
    else:require(not any(j['state']=='running' for j in active),'Native running task omitted from slot')
    worker=snapshot['worker_pid'];require(worker is None or type(worker) is int and worker>0,'Invalid native worker slot PID')
    if not active:
        require(snapshot['running'] is None and snapshot['queued']==[] and worker is None and snapshot['worker_alive'] is False,
                'Empty native slot retained a process/queue')
    if snapshot['state']=='closed':_idle(snapshot,closed=True)


def native_snapshots(data):
    """Never recurse through graph/business fields with coincident key names."""
    cpu,queue,closing=data['cpuCancel'],data['queue'],data['fifoRecoveryClose']
    result=[e['snapshot'] for e in cpu['phaseEvents']]+[cpu['afterCancel'],cpu['afterRecovery']]
    result.extend(queue[k] for k in ('started','queued','afterQueuedCancel','afterFirstReturn'))
    result.extend(closing[k] for k in ('fifo','idleBeforeClose','closed'))
    for key in ('close','externalCrash'):
        result.extend(data['resourceActions'][key][k] for k in ('running','after'))
    result.extend([data['resourceActions']['externalCrash']['afterRecovery'],data['resourceActions']['timeout']['after']])
    result.extend(data['overlapAndLoop']['overlap']['snapshots']);result.extend(data['overlapAndLoop']['overlap']['after'])
    result.extend(data['overlapAndLoop']['crossLoop'][k] for k in ('running','after'))
    return result


def validate_native_observation(value, installed, root=ROOT):
    root=Path(root);request=load(root/NATIVE_REQUEST)
    require(value["schema"]=="py-elk-e08-native-observation/v2" and value["requestSha256"]==NATIVE_REQUEST_SHA,"Native observation identity differs")
    equal(value["sourceSha256"],native_sources(root),"Native capture helpers/contracts changed")
    engine=value["engine"]
    require(type(engine['pid']) is int and engine['pid']>0 and type(engine['parentPid']) is int and engine['parentPid']>0 and engine['pid']!=engine['parentPid'],
            'Native actual capture process identity differs')
    require(engine["name"]=="pyelk" and engine["isolated"] is True and engine["modulePath"]==installed["modulePath"] and
            engine["version"]==installed["version"] and engine["python"]==installed["python"] and engine["packageFilesSha256"]==installed["packageFilesSha256"],"Native installed identity differs")
    data=value["lifecycle"];metadata=data["metadata"];expected=native_metadata_contract(root)
    interval=value['captureInterval']
    require(set(interval)=={'clock','started','finished'} and interval['clock']=='time.monotonic' and finite_number(interval['started']) and finite_number(interval['finished']) and
            0<=interval['started']<interval['finished'],'Invalid native capture monotonic interval')
    for snapshot in native_snapshots(data):
        validate_snapshot(snapshot,interval)
        require(all(job['pid']!=engine['pid'] for job in snapshot['jobs']),'Native CPU ran in the capture/event-loop process')
    for group in ("default","algorithmsEmpty"):
        for key,wanted in expected[group].items():
            equal(metadata[group][key],wanted,"Native metadata differs from independently audited contract")
            equal(metadata[group][key+"AfterMutation"],wanted,"Caller metadata mutation leaked")
    equal(metadata["defaultAfterEmpty"],expected["default"]["algorithms"],"Native instance registry leaked")
    require(set(metadata["closedErrors"])==set(METHODS),"Closed query denominator differs")
    for error in metadata["closedErrors"].values():
        native_error(error,'ResourceClosedError','RESOURCE_CLOSED','','The native instance is closed')
    native_error(metadata['emptyLayoutError'],'UnsupportedAlgorithmError','ALGORITHM_NOT_REGISTERED','/constructor/algorithms','The instance has no registered native layout algorithm')
    errors=data['publicErrors']
    for key,path in [('constructorUnknown','/constructor/algorithms/0'),('globalUnknownLocalValid','/constructor/defaultLayoutOptions/elk.algorithm')]:
        native_error(errors[key],'UnknownAlgorithmError','UNKNOWN_ALGORITHM',path,'Unknown algorithm identifier: V_UNKNOWN')
    for key,path in [('constructorUnsupported','/constructor/algorithms/0'),('globalUnsupportedLocalValid','/constructor/defaultLayoutOptions/elk.algorithm')]:
        native_error(errors[key],'UnsupportedAlgorithmError','UNSUPPORTED_ALGORITHM',path,'Known algorithm is not implemented: org.eclipse.elk.stress')
    native_error(errors['constructorContainer'],'OptionValidationError','INVALID_OPTION_VALUE','/constructor/algorithms','Expected a list of algorithm strings')
    native_error(errors['constructorWorker'],'UnsupportedWorkerError','UNSUPPORTED_WORKER','/constructor/workerFactory','JavaScript worker construction is unavailable in the native host')
    for key,path in [('logging','/layoutArguments/logging'),('timing','/layoutArguments/measureExecutionTime')]:
        message = ('Logging/timing flags must be booleans' if (root/'references/e09-host-contract.json').is_file()
                   else 'Logging/timing is outside this slice acceptance')
        native_error(errors[key],'UnsupportedFeatureError','UNSUPPORTED_SLICE',path,message)
    require(geometry(request['smallRequest'],{'outcome':'returned','result':errors['emptyCallReplacesBadConstructor']},request['smallGeometryPolicy'])['passed'] is True,
            'Call empty mapping did not replace constructor defaults')
    cpu=data["cpuCancel"];events=cpu["phaseEvents"]
    require(type(events) is list and len(events)>=2 and cpu["taskDoneBeforeCancel"] is False,"Missing actual running CPU cancellation interval")
    phases=[]
    clocks=[event['observedAt'] for event in events]+[cpu['cancelRequestedAt']]+cpu['heartbeats']
    require(bool(cpu['heartbeats']) and all(finite_number(clock) and interval['started']<=clock<=interval['finished'] for clock in clocks),'Invalid actual native observation/heartbeat clock')
    for event in events:
        snapshot=event["snapshot"];running=snapshot["running"]
        job=next(j for j in snapshot["jobs"] if j["job_id"]==running)
        progress=job["progress"]
        require(job["state"]=="running" and job["reaped"] is False and job["pid"]==cpu["pidBeforeCancel"]["pid"] and
                type(progress["index"]) is int and progress["index"]>=1 and progress["previous_outcome"]=="returned" and
                finite_number(progress["process_time"]) and progress["process_time"]>0,
                "CPU proof lacks actual completed native phase")
        phases.append(progress)
    require(phases[-1]["index"]>phases[0]["index"] and phases[-1]["process_time"]>phases[0]["process_time"],"Actual native CPU did not advance during observed interval")
    require(events[0]["observedAt"]<events[-1]["observedAt"]<=cpu["cancelRequestedAt"] and
            any(events[0]["observedAt"]<=tick<events[-1]["observedAt"] for tick in cpu["heartbeats"]),"Event-loop heartbeat did not overlap actual phase/CPU progress")
    _os_pid(cpu["pidBeforeCancel"],True);_os_pid(cpu["pidAfterCancel"],False)
    require(cpu["pidBeforeCancel"]["pid"]==cpu["pidAfterCancel"]["pid"],"Cancelled PID changed")
    _idle(cpu["afterCancel"]);_idle(cpu["afterRecovery"])
    cancelled=next(j for j in cpu["afterCancel"]["jobs"] if j["pid"]==cpu["pidBeforeCancel"]["pid"])
    require(cancelled["state"]=="cancelled" and cancelled["reaped"] is True and type(cancelled["exitcode"]) is int,"Cancellation returned before actual reap")
    require(cpu["inputBeforeSha256"]==cpu["inputAfterSha256"]==hashlib.sha256(json.dumps(request["cpuGraph"],sort_keys=True,separators=(',',':')).encode()).hexdigest(),"Running input was modified")
    small=request["smallRequest"]
    for result in (cpu["recoveryResult"],data["fifoRecoveryClose"]["recoveryResult"]):
        require(geometry(small,{"outcome":"returned","result":result},request["smallGeometryPolicy"])["passed"] is True,"Native recovery result violates original graph geometry")
    queue=data["queue"];queued_id=queue["queuedJobId"]
    require(queued_id in queue["queued"]["queued"] and queue["queued"]["pending"]==2 and queue["queueFullError"]["type"]=="QueueFullError" and
            queue["queueFullError"]["code"]=="QUEUE_FULL","Queue capacity/queued evidence differs")
    job=next(j for j in queue["afterFirstReturn"]["jobs"] if j["job_id"]==queued_id)
    require(job["state"]=="cancelled" and job["pid"] is None and job["started_at"] is None and job["reaped"] is True,"Queued cancellation started a process")
    equal(queue["lastTrace"],[],"Older success overwrote latest cancelled/error trace")
    _idle(queue["afterFirstReturn"])
    closing=data["fifoRecoveryClose"];jobs=closing["fifo"]["jobs"]
    require(len(jobs)==2 and [j["job_id"] for j in jobs]==[1,2] and all(j["state"]=="returned" and j["reaped"] is True for j in jobs) and
            jobs[0]["finished_at"]<=jobs[1]["started_at"],"Same-instance FIFO/single-slot evidence differs")
    native_error(closing['validationError'],'ModelValidationError','UNKNOWN_ENDPOINT','/edges/0/targets/0','Referenced node or port does not exist')
    equal(closing["traceAfterFailure"],[],"Failure retained old trace")
    require(bool(closing["traceAfterCallerMutation"]) and closing["traceAfterCallerMutation"][0]["processor"]!="V_MUTATION","Caller trace mutation leaked")
    _idle(closing["idleBeforeClose"]);_idle(closing["closed"],closed=True)
    native_error(closing['closedError'],'ResourceClosedError','RESOURCE_CLOSED','','The native instance is closed')
    actions=data['resourceActions']
    for name in ('close','externalCrash'):
        action=actions[name];snapshot=action['running'];job=next(j for j in snapshot['jobs'] if j['job_id']==snapshot['running'])
        require(action['taskDoneBeforeAction'] is False and job['progress']['index']>=1 and job['progress']['previous_outcome']=='returned',
                'Resource action did not interrupt a real phase-running native job')
        _os_pid(action['osPidBefore'],True);_os_pid(action['osPidAfter'],False)
        require(action['osPidBefore']['pid']==action['osPidAfter']['pid']==job['pid'],'Resource action PID differs')
        _idle(action['after'],closed=name=='close')
        ended=next(j for j in action['after']['jobs'] if j['pid']==job['pid'])
        require(ended['state']=='failed' and ended['reaped'] is True and type(ended['exitcode']) is int and ended['exitcode']!=0,
                'Interrupted native worker was not reaped with actual exit status')
        require(action['error']['type']==('ResourceClosedError' if name=='close' else 'WorkerExecutionError'),'Resource close/crash was relabeled')
        equal(action['lastTrace'],[],'Interrupted worker retained published trace')
        if name=='externalCrash':
            require(action['action']['pid']==job['pid'] and action['action']['method'] in ('TerminateProcess','kill(SIGKILL)'),
                    'Worker crash is not an actual external OS termination')
            _idle(action['afterRecovery'])
            require(geometry(small,{'outcome':'returned','result':action['recoveryResult']},request['smallGeometryPolicy'])['passed'] is True,
                    'Actual worker crash did not recover original graph geometry')
    timeout=actions['timeout'];_idle(timeout['after'])
    require(timeout['timeoutSeconds']==0.001 and finite_number(timeout['elapsedSeconds']) and timeout['elapsedSeconds']>=0.001 and
            timeout['error']['type']=='ExecutionTimeoutError' and timeout['error']['code']=='EXECUTION_TIMEOUT',
            'Actual submission/startup deadline evidence differs')
    require(bool(timeout['after']['jobs']) and all(j['state']=='failed' and j['reaped'] is True for j in timeout['after']['jobs']),
            'Timed-out native jobs were not reaped')
    require([p['pid'] for p in timeout['osPidsAfter']]==[j['pid'] for j in timeout['after']['jobs'] if j['pid'] is not None],
            'Timed-out process PID denominator differs')
    for pid in timeout['osPidsAfter']:_os_pid(pid,False)
    overlap=data['overlapAndLoop']['overlap']
    require(len(overlap['snapshots'])==len(overlap['osPids'])==len(overlap['after'])==2 and overlap['tasksDone']==[False,False],
            'Actual multi-instance overlap denominator differs')
    require(overlap['osPids'][0]['pid']!=overlap['osPids'][1]['pid'],'Multi-instance workers share one PID')
    for snapshot,pid,after in zip(overlap['snapshots'],overlap['osPids'],overlap['after']):
        job=next(j for j in snapshot['jobs'] if j['job_id']==snapshot['running'])
        require(job['pid']==pid['pid'] and job['progress']['index']>=1 and job['progress']['previous_outcome']=='returned',
                'Overlap lacks independently executing native phase progress')
        _os_pid(pid,True);_idle(after)
    loops=data['overlapAndLoop']['crossLoop']
    require(loops['running']['pending']>0 and loops['error']['type']=='ExecutionError' and loops['error']['code']=='EVENT_LOOP_CONFLICT',
            'Active cross-loop conflict was not explicitly rejected')
    _idle(loops['after'])
    for key in ('otherLoopResult','originalLoopResult'):
        require(geometry(small,{'outcome':'returned','result':loops[key]},request['smallGeometryPolicy'])['passed'] is True,
                'Idle loop rebinding changed actual layout geometry')
    return {"status":"E08_NATIVE_API_LIFECYCLE_OBSERVATION_VALIDATED","passed":True}


def validate_observation_independence(observations, launcher_pid):
    """Lifecycle bodies contain real process/clock observations, unlike layouts."""
    canonical_bodies=set();capture_pids=set();previous_finished=None
    for observation in observations:
        canonical=hashlib.sha256(json.dumps(observation,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        require(canonical not in canonical_bodies,'Native independent repetitions reused canonical observation body')
        canonical_bodies.add(canonical)
        # Windows venv launchers can insert an actual intermediary process.
        # Keep its observed parent PID; do not invent direct parentage to the
        # orchestration interpreter without a separately observed process tree.
        pid=observation['engine']['pid'];parent=observation['engine']['parentPid']
        require(type(pid) is int and pid not in capture_pids and pid!=launcher_pid and type(parent) is int and parent>0 and parent!=pid,
                'Native independent capture process identity reused/differs')
        capture_pids.add(pid)
        interval=observation['captureInterval']
        require(previous_finished is None or previous_finished<=interval['started'],'Native sequential capture monotonic intervals overlap/replay')
        previous_finished=interval['finished']


def validate_candidate_receipt(value, root=ROOT):
    """Portable, pure evidence checks; never trusts a saved PASS flag."""
    root=Path(root)
    require(value["schema"]=="py-elk-e08-native-runtime-receipt/v1","Unknown native receipt schema")
    raw=base64.b64decode(value["requestBytesBase64"],validate=True)
    require(hashlib.sha256(raw).hexdigest()==NATIVE_REQUEST_SHA and raw==(root/NATIVE_REQUEST).read_bytes(),"Native receipt original request differs")
    require(type(value["repeat"]) is int and value["repeat"]>=3 and len(value["captures"])==value["repeat"],"Independent native repeat denominator differs")
    require(len({c['observationSha256'] for c in value['captures']})==value['repeat'],'Native independent repetitions reused raw observation bytes')
    equal(value["sourceSha256"],native_sources(root),"Current native verifier/helper/contract bytes differ")
    installed=value["installed"]
    require(installed["status"]=="INSTALLED_WHEEL_BYTES_MATCH" and installed["isolatedInterpreter"] is True,"Real installed-wheel identity missing")
    source=original_path(value["actualSourceRoot"]);origin=original_path(value["actualExecutionRoot"])
    identity=value['installedCommand'];command=identity['command']
    require(command['argv']==[value['candidatePython'],'-I',str(source/'scripts/verify_installed_wheel.py'),value['wheel'],'--out',str(origin/'installed-wheel.json')] and
            command['cwd']==str(source) and type(command['exitCode']) is int and command['exitCode']==0 and command['timedOut'] is False,
            'Actual installed-wheel command identity differs')
    for stream in ('stdout','stderr'):
        require(hashlib.sha256(base64.b64decode(identity[stream+'BytesBase64'],validate=True)).hexdigest()==command[stream+'Sha256'],
                'Actual installed-wheel command log differs')
    equal(embedded_json(base64.b64decode(value['installedReceiptBytesBase64'],validate=True)),installed,'Actual installed-wheel receipt bytes differ')
    observations=[]
    require(type(value['launcherPid']) is int and value['launcherPid']>0,'Native launcher process identity missing')
    for ordinal,capture in enumerate(value["captures"]):
        require(type(capture["repetition"]) is int and capture["repetition"]==ordinal,"Native process repetition slot differs")
        command=capture["command"];relative="native-capture/repeat-"+str(ordinal)+"/observation.json"
        expected=[value["candidatePython"],"-I",str(source/"scripts/validate_e08_api.py"),"--candidate-capture",str(origin/"native-request.json"),str(origin/relative)]
        require(command["argv"]==expected and command["cwd"]==str(source) and type(command["exitCode"]) is int and command["exitCode"]==0 and command["timedOut"] is False,"Actual installed native command/isolation/exit differs")
        equal(capture["environmentPolicy"],{"pathEmpty":True,"overridesAbsent":True},"Actual native environment policy differs")
        for stream in ("stdout","stderr"):
            require(hashlib.sha256(base64.b64decode(capture[stream+"BytesBase64"],validate=True)).hexdigest()==command[stream+"Sha256"],"Actual native command log bytes differ")
        observed=base64.b64decode(capture["observationBytesBase64"],validate=True)
        require(hashlib.sha256(observed).hexdigest()==capture["observationSha256"],"Native raw observation bytes differ")
        observation=embedded_json(observed)
        observations.append(observation)
        require(observation["engine"]["executable"]==value["candidatePython"],"Native actual interpreter differs")
        validate_native_observation(observation,installed,root)
    validate_observation_independence(observations,value['launcherPid'])
    return {"status":"E08_NATIVE_API_LIFECYCLE_RECEIPT_VALIDATED","passed":True,"repeat":value["repeat"],
            "actualCaptureProcesses":value["repeat"],"pythonAlgorithmsVerified":0,"historicalExecutionAuthenticated":False,
            "scope":"metadata isolation; real native CPU heartbeat/running cancellation/reap/recovery; actual queued cancellation/capacity/FIFO; active close/external OS worker crash/submission-startup deadline cleanup; real two-worker overlap; active loop rejection/idle loop rebinding; failure/trace/closed behavior. No hard CPU/memory limit or statistical throughput claim."}


def capture_candidate(out, python, wheel, repeat=3):
    require(type(repeat) is int and repeat>=3,"Use at least three independent installed captures")
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    python=str(Path(python).resolve());wheel=Path(wheel).resolve()
    env=os.environ.copy()
    for key in list(env):
        if key.upper() in ("NODE_OPTIONS","NODE_PATH","PYTHONPATH","PYTHONHOME"):env.pop(key)
    env['PATH']=''
    folder=out/'installed-wheel-command';folder.mkdir()
    record=run([python,'-I',str(ROOT/'scripts/verify_installed_wheel.py'),str(wheel),'--out',str(out/'installed-wheel.json')],folder,120,env=env)
    require(type(record['exitCode']) is int and record['exitCode']==0 and record['timedOut'] is False,"Actual installed-wheel verification failed")
    installed=load(out/'installed-wheel.json');shutil.copyfile(ROOT/NATIVE_REQUEST,out/'native-request.json')
    installed_command={'command':record,**{s+'BytesBase64':base64.b64encode((folder/(s+'.log')).read_bytes()).decode() for s in ('stdout','stderr')}}
    captures=[]
    for ordinal in range(repeat):
        folder=out/'native-capture'/('repeat-'+str(ordinal));folder.mkdir(parents=True)
        record=run([python,'-I',str(ROOT/'scripts/validate_e08_api.py'),'--candidate-capture',str(out/'native-request.json'),str(folder/'observation.json')],folder,120,env=env)
        require(type(record['exitCode']) is int and record['exitCode']==0 and record['timedOut'] is False,"Actual native API/lifecycle process failed")
        captures.append({'repetition':ordinal,'command':record,'environmentPolicy':{'pathEmpty':True,'overridesAbsent':True},
            'observationBytesBase64':base64.b64encode((folder/'observation.json').read_bytes()).decode(),
            'observationSha256':sha256(folder/'observation.json'),**{s+'BytesBase64':base64.b64encode((folder/(s+'.log')).read_bytes()).decode() for s in ('stdout','stderr')}})
    value={'schema':'py-elk-e08-native-runtime-receipt/v1','repeat':repeat,'actualSourceRoot':str(ROOT),'actualExecutionRoot':str(out),
           'launcherPid':os.getpid(),
           'candidatePython':python,'installed':installed,'sourceSha256':native_sources(),'captures':captures,
           'wheel':str(wheel),'installedCommand':installed_command,
           'installedReceiptBytesBase64':base64.b64encode((out/'installed-wheel.json').read_bytes()).decode(),
           'requestBytesBase64':base64.b64encode((out/'native-request.json').read_bytes()).decode()}
    write(out/'receipt.json',value)
    result=validate_candidate_receipt(value);write(out/'report.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--with-reference",action="store_true")
    parser.add_argument("--package",type=Path,default=ROOT/".local/npm-elkjs/package")
    parser.add_argument("--node",default="node")
    parser.add_argument("--verify-reference",type=Path)
    parser.add_argument("--candidate-python",type=Path)
    parser.add_argument("--wheel",type=Path)
    parser.add_argument("--repeat",type=int,default=3)
    parser.add_argument("--candidate-capture",nargs=2,type=Path,metavar=("REQUEST","OUTPUT"))
    parser.add_argument("--verify-candidate",type=Path)
    args=parser.parse_args()
    try:
        if args.candidate_capture:result=candidate_capture(*args.candidate_capture)
        elif args.verify_candidate:result=validate_candidate_receipt(load(args.verify_candidate))
        elif args.candidate_python:
            require(args.out is not None and args.wheel is not None,"Candidate capture requires --out and --wheel")
            result=capture_candidate(args.out,args.candidate_python,args.wheel,args.repeat)
        elif args.with_reference:
            require(args.out is not None,"--with-reference requires a new --out directory")
            result=capture_reference(args.out,args.package,args.node)
        elif args.verify_reference:result=verify_reference(args.verify_reference)
        else:
            result=check()
            if args.out:write(args.out,result)
        print(json.dumps(result,indent=2));return 0 if result["passed"] else 1
    except (ValueError,OSError,KeyError,TypeError,IndexError) as e:
        print(json.dumps({"status":"FAIL","passed":False,"error":str(e)}),file=sys.stderr);return 2


if __name__=="__main__":raise SystemExit(main())
