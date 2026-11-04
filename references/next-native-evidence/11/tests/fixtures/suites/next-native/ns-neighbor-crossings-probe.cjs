const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__nsNeighbor=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LNode$NodeType();
 const g=new LGraph,l=new Layer(g),nodes={},ports={},side={NORTH:NORTH_3,SOUTH:SOUTH_2,EAST:EAST_2,WEST:WEST_2},kind={NORMAL,NORTH_SOUTH_PORT,LONG_EDGE};$add_3(g.layers,l);
 s.nodes.forEach(([id,type],i)=>{const n=nodes[id]=new LNode(g);$setType(n,kind[type]);$setLayer(n,i,l);});
 for(const [id,owner,ps] of s.ports){const p=ports[id]=new LPort;$setNode(p,nodes[owner]);$setSide(p,side[ps]);}
 for(const [dummy,origin] of s.dummyOrigins){$setProperty_0(nodes[dummy],ORIGIN_0,ports[origin].owner);$setProperty_0(nodes[dummy].ports.array[0],ORIGIN_0,ports[origin]);}
 s.portDummies.forEach(([p,n])=>$setProperty_0(ports[p],PORT_DUMMY,nodes[n]));
 for(const [a,b] of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const row=s.nodes.map(([id])=>nodes[id]),c=new NorthSouthEdgeNeighbouringNodeCrossingsCounter(row),counts=[];
 s.queries.forEach(([a,b])=>{$countCrossings(c,nodes[a],nodes[b]);counts.push([c.upperLowerCrossings,c.lowerUpperCrossings]);});
 return {counts,positions:Object.entries(ports).filter(([id,p])=>$containsKey_3(c.portPositions,p)).map(([id,p])=>[id,$get_10(c.portPositions,p).value_0]),rowIdentity:c.layer===row,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__nsNeighbor(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-ns-neighbor-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
