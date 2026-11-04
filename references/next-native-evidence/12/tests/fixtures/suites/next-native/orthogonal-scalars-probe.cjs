// Three general numeric leaves of real source helpers; no full geometry run.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__orthogonalScalars=function(s){
 getInstance();$clinit_HyperEdgeSegmentDependency$DependencyType();
 const a=new HyperEdgeSegment(null),b=new HyperEdgeSegment(null);
 for(const weight of s.weights)new HyperEdgeSegmentDependency(REGULAR,a,b,weight);
 const segments=new ArrayList;$add_3(segments,a);$add_3(segments,b);const sources=new LinkedList,sinks=new LinkedList;
 initialize_2(segments,sources,sinks,false);
 const array=list=>{const out=[],it=list.iterator_0();while(it.hasNext_0())out.push(it.next_1());return out;};
 const decode=value=>value==='NaN'?NaN:value;
 const numbers=new ArrayList;for(const value of s.minimumDifference)$add_3(numbers,decode(value));
 const minimum=$minimumDifference(new StreamImpl(null,new Spliterators$IteratorSpliterator(numbers,16)));
 const strategy=new BaseRoutingDirectionStrategy,edge=new LEdge,segment=new HyperEdgeSegment(null);
 segment.startPosition=s.junction.segmentStart;segment.endPosition=s.junction.segmentEnd;
 const pos=new KVector_1(decode(s.junction.x),s.junction.y);
 for(let i=0;i<s.junction.repeats;i++)$addJunctionPointIfNecessary(strategy,edge,segment,pos,true);
 const junctions=$getProperty(edge,($clinit_LayeredOptions(),JUNCTION_POINTS));
 const number=value=>Number.isNaN(value)?{kind:'NaN'}:value===Infinity?{kind:'Infinity'}:value===-Infinity?{kind:'-Infinity'}:{kind:'finite',value,negativeZero:Object.is(value,-0)};
 return {weights:{out:a.outDepWeight,in:b.inDepWeight,marks:[a.mark,b.mark],sources:array(sources).map(n=>n===a?'a':'b'),sinks:array(sinks).map(n=>n===a?'a':'b')},minimumDifference:number(minimum),junctionCount:junctions.size_0,junctions:array(junctions).map(p=>({x:number(p.x_0),y:number(p.y_0)})),layoutExecuted:false,validFiniteGeometry:false,internalNumericLeavesOnly:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__orthogonalScalars(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-orthogonal-scalars-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
