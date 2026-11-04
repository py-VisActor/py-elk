const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__modelFeedback=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_OrderingStrategy();$clinit_LNode$NodeType();$clinit_LongEdgeOrderingStrategy();
 const g=new LGraph,nodes={},ports={};
 for(const [id,type,order] of s.nodes){const n=nodes[id]=new LNode(g);$setType(n,type==='NORMAL'?NORMAL:LONG_EDGE);if(order!==null)$setProperty_0(n,MODEL_ORDER_2,valueOf_3(order));}
 for(const [id,owner,side] of s.ports){const p=ports[id]=new LPort;$setNode(p,nodes[owner]);$setSide(p,side==='EAST'?EAST_2:WEST_2);}
 const layers=s.layers.map((ids,i)=>{const l=new Layer(g);l.id_0=i;$add_3(g.layers,l);ids.forEach((id,j)=>$setLayer(nodes[id],j,l));return ids.map(id=>nodes[id]);});
 for(const [a,b,order] of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);$setProperty_0(e,MODEL_ORDER_2,valueOf_3(order));}
 $setProperty_0(g,MAX_MODEL_ORDER_NODES,valueOf_3(s.nodes.length));
 const cmp=new ModelOrderNodeComparator_1(g,layers[0],PREFER_EDGES,EQUAL);cmp.beforePorts=true;
 const results=s.cyclicQueries.map(([a,b])=>$compare_17(cmp,nodes[a],nodes[b]));
 function relation(c,mapName){const map=c[mapName];return s.nodes.map(([a])=>({id:a,present:$containsKey_3(map,nodes[a]),members:s.nodes.filter(([b])=>$containsKey_3(map,nodes[a])&&$contains_6($get_10(map,nodes[a]),nodes[b])).map(([b])=>b)}));}
 const recursive=new ModelOrderNodeComparator_1(g,layers[0],PREFER_EDGES,EQUAL),recursiveResult=$compare_17(recursive,nodes[s.recursiveQuery[0]],nodes[s.recursiveQuery[1]]);
 return {results,bigger:relation(cmp,'biggerThan'),smaller:relation(cmp,'smallerThan'),recursiveResult,recursiveBigger:relation(recursive,'biggerThan'),recursiveSmaller:relation(recursive,'smallerThan'),layoutExecuted:false,suppliedInternalModelOrder:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__modelFeedback(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-model-feedback-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
