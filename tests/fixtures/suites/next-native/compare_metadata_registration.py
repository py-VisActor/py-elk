"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; metadata only, no layouts."""
import hashlib,json,sys
from pathlib import Path
source,request_path,oracle_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.metadata._registration_data import LEGACY_IDS
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
assert sha(request_path)==oracle['requestSha256']
def snapshot(service):
    return {'algorithms':list(service.registry.algorithms),
      'options':[{'id':name,'legacyIds':list(LEGACY_IDS.get(name,()))}for name in service.option_ids],
      'categories':[row['id']for row in service.categories()],
      'lookups':[{'query':q,'id':service.lookup_option(q)}for q in request['queries']]}
groups=[]
for group in request['groups']:
    service=NativeMetadataService(group['algorithms'])
    groups.append({'name':group['name'],'registered':group['algorithms'],**snapshot(service)})
service=NativeMetadataService([]);warm=[]
for names in request['warmSequence']:
    service.register(names);warm.append({'registered':names,**snapshot(service)})
actual={'groups':groups,'warm':warm}
comparison=diff(oracle['observation'],actual,tolerant=False)
assert comparison['passed'],comparison
# Existing immutable public metadata captures check new private getter content.
default=NativeMetadataService();getters={};bindings={}
for kind in('algorithms','options','categories'):
    reference=Path('references/metadata')/(kind+'.json');bindings[reference.as_posix()]=sha(reference)
    getters[kind]=diff(json.loads(reference.read_text('utf-8')),getattr(default,kind)(),tolerant=False)
    assert getters[kind]['passed'],(kind,getters[kind])
    first=getattr(default,kind)();first[0]['name']='caller mutation'
    assert getattr(default,kind)()[0]['name']!='caller mutation'
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':True,'comparison':comparison,'actual':actual,
 'publicMetadataGetterComparisons':getters,'publicMetadataBindings':bindings,
 'sourceSha256':before,'oracleSha256':sha(oracle_path),'checkerSha256':sha(Path(__file__)),
 'metadataOnly':True,'originalReexecuted':False,'layoutExecuted':False,'publicAPIIntegrated':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':True,'registrationGroups':len(groups),'warmRegistrationSteps':len(warm),'publicMetadataCounts':[12,243,8],'layoutsExecuted':0}))
