// Actual Spacings object, nullable property matrices and concrete node getters.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__spacings=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_LNode$NodeType();
 const g=new LGraph,properties={SPACING_NODE_NODE_0,SPACING_NODE_NODE_BETWEEN_LAYERS_0,SPACING_EDGE_NODE,SPACING_EDGE_NODE_BETWEEN_LAYERS_0,SPACING_EDGE_EDGE,SPACING_EDGE_EDGE_BETWEEN_LAYERS_0,SPACING_LABEL_NODE,SPACING_PORT_PORT,SPACING_LABEL_PORT_VERTICAL,SPACING_LABEL_PORT_HORIZONTAL};
 for(const [key,value]of Object.entries(s.graphValues))$setProperty_0(g,properties[key],value);
 const spacing=new Spacings(g),types=[NORMAL,LONG_EDGE,EXTERNAL_PORT,NORTH_SOUTH_PORT,LABEL,BREAKING_POINT,PLACEHOLDER,NONSHIFTING_PLACEHOLDER];
 const view=matrix=>matrix.map(row=>row.map(p=>p===null?null:p.id_0));
 const queries=[];for(const [axis,matrix]of [['vertical',spacing.nodeTypeSpacingOptionsVertical],['horizontal',spacing.nodeTypeSpacingOptionsHorizontal]]){
  for(let a=0;a<types.length;a++)for(let b=0;b<types.length;b++)if(matrix[a][b]!=null)queries.push({axis,a,b,value:axis==='vertical'?$getVerticalSpacing(spacing,types[a],types[b]):$getHorizontalSpacing(spacing,types[a],types[b])});}
 const first=new LNode(g),second=new LNode(g);first.type_0=NORMAL;second.type_0=LONG_EDGE;
 const a=new MapPropertyHolder,b=new MapPropertyHolder;$setProperty(a,SPACING_EDGE_NODE,s.individualValues[0]);$setProperty(b,SPACING_EDGE_NODE,s.individualValues[1]);$setProperty_0(first,SPACING_INDIVIDUAL,a);$setProperty_0(second,SPACING_INDIVIDUAL,b);
 const saved=getIndividualOrDefault,calls=[];getIndividualOrDefault=function(node,p){calls.push(node===first?'first':'second');return saved(node,p);};
 const pairs=[];try{
  pairs.push($getVerticalSpacing_0(spacing,first,second));
  $setProperty_0(second,SPACING_INDIVIDUAL,null);pairs.push($getVerticalSpacing_0(spacing,first,second));
  $setProperty_0(first,SPACING_INDIVIDUAL,null);const layer=new Layer(g);$setLayer_0(second,layer);second.graph_0=null;pairs.push($getVerticalSpacing_0(spacing,first,second));
 }finally{getIndividualOrDefault=saved;}
 return {vertical:view(spacing.nodeTypeSpacingOptionsVertical),horizontal:view(spacing.nodeTypeSpacingOptionsHorizontal),queries,pairs,calls,individualAbsentAfterRemove:!$hasProperty(first,SPACING_INDIVIDUAL)&&!$hasProperty(second,SPACING_INDIVIDUAL),layerGraphFallback:$getGraph(second)===g,sourceObjectApi:true,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__spacings(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-spacings-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
