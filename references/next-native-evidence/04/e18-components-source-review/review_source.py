import json,hashlib,base64,re
from pathlib import Path
sha=lambda b:hashlib.sha256(b).hexdigest()
p=Path('references/e18-force-stress-sources.json');raw=p.read_bytes();assert sha(raw)=='24c7688042a22d95179e00e446fc6a4873f4d44be3058522ea79b509c0a33f02'
w=Path('.local/npm-elkjs/package/lib/elk-worker.js');wr=w.read_bytes();assert sha(wr)=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86';text=wr.decode();lines=text.splitlines()
d=json.loads(raw);c=next(c for c in d['components'] if c['id']=='F04');blob=('\n'.join(lines[c['lineStart']-1:c['lineEnd']])+'\n').encode();assert blob==base64.b64decode(c['sourceBytesBase64'],validate=True) and sha(blob)==c['spanSha256']
support=[]
for name,start,end in [('shallow copyProperties',25418,25426),('source Integer boxing no truncation',11371,11377),('source Double total comparator',11187,11198),('LinkedList parent',16544,16560),('AbstractSequentialList parent',6473,6473),('AbstractList comparator dispatch',6339,6343),('default list sort toArray/mergeSort/set',2142,2149),('mergeSort entry',14495,14500),('Force BB property keys',27845,27846)]:
 b=('\n'.join(lines[start-1:end])+'\n').encode();support.append(dict(symbol=name,startLine=start,endLine=end,sha256=sha(b),sourceBytesBase64=base64.b64encode(b).decode()))
for name in ['$intern_0','$intern_44']:
 m=re.search(re.escape(name)+r' = -?[0-9]+',text);assert m; b=m.group().encode();support.append(dict(symbol=name,startByte=m.start(),endByteExclusive=m.end(),sha256=sha(b),sourceBytesBase64=base64.b64encode(b).decode()))
result={'accepted':True,'blockers':[],'acceptedComponentIds':['F04'],'filesSha256':{str(p).replace('\\','/'):sha(raw),str(w).replace('\\','/'):sha(wr)},'reviewerRole':'Root independent of B proposal/production author; exact worker bytes and callers read directly','scope':'Force ComponentsProcessor source closure only; no native implementation execution or whole provider acceptance','componentSpanSha256':sha(blob),'supplementarySourceSpans':support,'implementationObligations':[
 'Incidence appends each edge to source then target lists, retaining duplicates and original order. Self-edge incidence occurs twice if a helper caller actually supplies one.',
 'DFS visited by current dense node id. Skip every edge incident with last node, not only the traversal edge; recurse source then target and append edge/labels after those calls. List edge duplicates for cycles and multiedges are source behavior; do not deduplicate.',
 'Use explicit iterator stack with identical call/unwind schedule for native traversal; no Python recursion-depth or graph-count admission cap.',
 'separate null/true splits, false returns the same graph in one list. Each new component shallow-copies original properties so RANDOM and mutable object references remain shared. Renumber node ids only when component count exceeds one.',
 'recombine size1 returns the same component without bounds/sort/move; empty returns a fresh FGraph. Multi-component bounds initialize at signed32 extrema2147483647/-2147483648, not infinity, and only use node center/halfsize.',
 'Priority is summed in generated JS Number arithmetic then boxed without signed32 truncation in valueOf_3; do not introduce int32 wrap or unlimited-int arithmetic changes. Comparator priority2-priority1 then ascending area using source Double total order.',
 'LinkedList inherits AbstractList sort->toArray->mergeSort->set; existing exact source_sort/Apache notice is reused rather than replacing comparator schedule.',
 'Copy properties from first sorted component to new result, preserve exact row-break comparison>x, spacing and aspect operations. moveGraph reuses/moves same node, bendpoint and label objects; no ownership cloning. Labels/edges lists retain encounter order and duplicates.'
 ],'license':'ELK ComponentsProcessor scoped algorithm under EPL-2.0 OR GPL-3.0-or-later; existing separately attributed GWT sort/Double helpers reused, no GWT/EMF framework or Integer class port licensed by this source approval','fullValidation':False,'nativeCodeReviewed':False,'wholeAlgorithmAccepted':False}
out=Path('test-runs/20261104-E18-01/root/f04-source-01/review.json');out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'accepted':True,'component':'F04','reviewSha256':sha(out.read_bytes()),'fullValidation':False}))
