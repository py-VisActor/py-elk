"""NEW_REPORT (REQUEST ORIGINAL SAVED_NATIVE)...; source-data checks only."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from layout_checks import diff
from recursive_observations import without_generated_hashes
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=Path(sys.argv[1]);args=sys.argv[2:];assert args and len(args)%3==0
files={};results=[]
for i in range(0,len(args),3):
    request_path,oracle_path,native_path=map(Path,args[i:i+3])
    request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
    native=json.loads(native_path.read_text('utf-8'));assert sha(request_path)==oracle['requestSha256']
    owned={};stack=[(request.get('graph',request),'/result','node')]
    while stack:
        element,path,kind=stack.pop();owned[path]=element
        groups=('labels','ports','children','edges')if kind=='node'else('labels',)if kind in('edge','port')else()
        for group in groups:
            child_kind={'labels':'label','ports':'port','children':'node','edges':'edge'}[group]
            for j,child in enumerate(element.get(group,())):stack.append((child,path+'/'+group+'/'+str(j),child_kind))
    comparison=diff(without_generated_hashes(oracle['observation'],owned),native['actual'],tolerant=False)
    assert comparison['passed'],comparison
    results.append({'native':str(native_path),'comparison':comparison})
    for path in(request_path,oracle_path,native_path):files[path.as_posix()]=sha(path)
probe={'$H':31,'business':{'$H':17},'children':[{'$H':8}]}
assert without_generated_hashes(probe,{'':{'$H':31},'/children/0':{}})=={'$H':31,'business':{'$H':17},'children':[{}]}
assert not diff({'business':{'$H':17}},{'business':{'$H':18}},tolerant=False)['passed']
for name in('recursive_observations.py','verify_recursive_saved.py'):
    path=Path(__file__).with_name(name);files[path.as_posix()]=sha(path)
with out.open('x',encoding='utf-8')as f:json.dump({'accepted':True,'blockers':[],'filesSha256':files,
 'savedComparisons':results,'userAndBusinessHashesRetained':True,'productsExecuted':0,'fullValidation':False},f,indent=2)
print(json.dumps({'strictSavedComparisons':len(results),'productsExecuted':0}))
