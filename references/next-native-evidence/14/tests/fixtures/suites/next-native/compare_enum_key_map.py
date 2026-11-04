"""PRIVATE_SRC ORIGINAL NEW_REPORT; instrumented collisions, no layout oracle."""
import hashlib,json,sys
from pathlib import Path
source,original,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.execution.enum_collections import EnumKeyMap,EnumSetKeyMap
from pyelk.execution.enum_identity import PORT_SIDE_DOMAIN,PORT_SIDE_ORDER,enum_symbol,enum_identity_hash
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
codes={'UNDEFINED':7,'NORTH':11,'EAST':11,'SOUTH':22,'WEST':13}
def set_hash(key):return (sum(codes[n]for n in PORT_SIDE_ORDER if n in key)+2147483648)%4294967296-2147483648
map=EnumSetKeyMap(PORT_SIDE_DOMAIN,PORT_SIDE_ORDER,hash_function=set_hash)
a={'NORTH','EAST'};b={'SOUTH'};c={'WEST'};events=[]
def snapshot(m,set_keys=True):return [{'key':None if k is None else sorted(k,key=PORT_SIDE_ORDER.index)if set_keys else k,'value':v}for k,v in m.items()]
def event(name,value):events.append({'name':name,'value':value,'items':snapshot(map)})
event('missing',map.get(a));event('put-a',map.put(a,'a'));event('put-b',map.put(b,'b'));event('put-c',map.put(c,'c'))
event('replace-equal-key',map.put({'NORTH','EAST'},'A'));same=map.keys()[0]is a
event('put-null-key',map.put(None,'null-key'));a.add('WEST');event('get-mutated-key',map.get(a));event('get-old-membership',map.get({'NORTH','EAST'}))
event('remove-b',map.remove(b));event('reinsert-b',map.put(b,'B'));event('remove-c',map.remove(c));event('reinsert-c',map.put(c,'C'))
scalar=EnumKeyMap(PORT_SIDE_DOMAIN,PORT_SIDE_ORDER,hash_function=codes.__getitem__)
scalar.put('NORTH',1);scalar.put('WEST',2);scalar.put('EAST',3);scalar_items=snapshot(scalar,False)
codes.update(NORTH=2147483647,EAST=3,SOUTH=-2147483646)
overflow=EnumSetKeyMap(PORT_SIDE_DOMAIN,PORT_SIDE_ORDER,hash_function=set_hash)
overflow.put({'NORTH','EAST'},'sum');overflow.put({'WEST'},'middle');overflow.put({'SOUTH'},'collision')
actual={'events':events,'storedKeySame':same,'scalarItems':scalar_items,'overflowItems':snapshot(overflow)}
raw=json.loads(original.read_text('utf-8'));assert raw['instrumentedEnumHashControl']is True
comparison=diff(raw['value'],actual,tolerant=False)
# Default native singleton scope is separate from the controlled collision codes.
assert enum_symbol(PORT_SIDE_DOMAIN,'NORTH')is enum_symbol(PORT_SIDE_DOMAIN,'NORTH')
assert enum_symbol(PORT_SIDE_DOMAIN,'NORTH')is not enum_symbol('another.Enum','NORTH')
assert enum_identity_hash(PORT_SIDE_DOMAIN,'NORTH')==enum_identity_hash(PORT_SIDE_DOMAIN,'NORTH')
bindings={}
for name in('enum_collections.py','enum_identity.py','identity.py'):
 p=source/'pyelk/execution'/name;bindings[p.relative_to(source).as_posix()]=sha(p)
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'sourceSha256':bindings,'originalSha256':sha(original),'checkerSha256':sha(Path(__file__)),
 'instrumentedEnumHashControl':True,'ordinaryLayoutOracle':False,'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences']),'ordinaryLayoutOracle':False}))
raise SystemExit(0 if comparison['passed']else 1)
