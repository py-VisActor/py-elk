// New original traversal/fill/container objects; no common packing execution.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__polyTraversal=function(s){
 $clinit_Direction();const al=xs=>{const a=new ArrayList;xs.forEach(v=>$add_3(a,v));return a;},pair=xy=>new Pair(valueOf_3(xy[0]),valueOf_3(xy[1])),xy=p=>[p.first.value_0,p.second.value_0];
 const make=()=>{const path=new LinkedList;[[0,0],[s.size[0],0],s.size,[0,s.size[1]]].forEach(v=>$add_7(path,new KVector_1(...v)));const c=new DCComponent;$addElements(c,al([new DCElement(path)]));const p=new DCPolyomino(c,1,1);for(let x=0;x<p.xSize;x++)for(let y=0;y<p.ySize;y++)$set_4(p,x,y,false,false);return p;};
 const p=make(),other=make(),sequences={};for(const [name,fn]of [['jitter',$apply_4],['lineByLine',$apply_5],['manhattan',$apply_6],['maxNorm',$apply_7]]){let at=pair(s.successorStart);sequences[name]=[];for(let i=0;i<s.successorSteps;i++){at=fn(at);sequences[name].push(xy(at));}}
 $add_3(p.polyominoExtensions,new UniqueTriple(EAST,valueOf_3(0),valueOf_3(0)));const q=new SuccessorQuadrantsGeneric(new SuccessorJitter),flags=()=>[q.posX,q.negX,q.posY,q.negY];
 const first=xy(q.apply_3(pair(s.quadrantStart),p)),firstFlags=flags();p.polyominoExtensions.clear_0();$add_3(p.polyominoExtensions,new UniqueTriple(WEST,valueOf_3(0),valueOf_3(0)));
 const stale=xy(q.apply_3(pair(s.quadrantStart),p)),staleFlags=flags();$add_3(other.polyominoExtensions,new UniqueTriple(WEST,valueOf_3(0),valueOf_3(0)));const refreshed=xy(q.apply_3(pair(s.quadrantStart),other)),refreshedFlags=flags();
 const combination=new SuccessorCombination(new SuccessorQuadrantsGeneric(new SuccessorLineByLine),new SuccessorQuadrantsGeneric(new SuccessorJitter));
 const combined=xy(combination.apply_3(pair(s.quadrantStart),p));p.polyominoExtensions.clear_0();const combinedWithoutExtensions=xy(combination.apply_3(pair(s.quadrantStart),p));
 s.strong.forEach(v=>$set_4(p,...v,false,true));s.weak.forEach(v=>$set_4(p,...v,true,false));const cells=g=>Array.from({length:g.ySize},(_,y)=>Array.from({length:g.xSize},(_,x)=>toInt_0($retrieve(g,x,y))));
 const before=cells(p),input=al([p,other]),container=new Polyominoes(input,s.aspectRatio,true);
 return {sequences,quadrants:{first,firstFlags,stale,staleFlags,refreshed,refreshedFlags,combined,combinedWithoutExtensions},fillBefore:before,fillAfter:cells(p),container:{size:[container.grid.xSize,container.grid.ySize],listOwned:container.polys!==input,polysShared:container.polys.array[0]===p&&container.polys.array[1]===other},layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__polyTraversal(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-polyomino-traversal-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
