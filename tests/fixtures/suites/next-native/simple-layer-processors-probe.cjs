// Execute two actual neighboring working-graph bodies, never full JSON layout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__simpleLayerProcessors=function(s){
 getInstance();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_InLayerConstraint();$clinit_LNode$NodeType();
 return {cases:s.cases.map(item=>{
  const g=new LGraph,names=new Map,layers=[],rows=[],initial=[],events=[];
  g.offset.y_0=item.offsetY;g.size_0.y_0=999;
  if(item.surrounding)$setProperty_0(g,SPACING_PORTS_SURROUNDING,new ElkMargin_1(...item.surrounding));
  const explicit=item.surrounding?$getProperty(g,SPACING_PORTS_SURROUNDING):null;
  item.layers.forEach((input,i)=>{const l=new Layer(g);$add_3(g.layers,l);l.size_0.x_0=83;l.size_0.y_0=97;layers.push(l);rows.push(l.nodes);initial.push(l.size_0);
   input.forEach(v=>{const n=new LNode(g);names.set(n,v.id);n.pos.y_0=v.y;n.size_0.x_0=v.width;n.size_0.y_0=v.height;[n.margin.top_0,n.margin.right,n.margin.bottom,n.margin.left]=v.margin;
    n.type_0=v.type==='EXTERNAL_PORT'?EXTERNAL_PORT:NORMAL;$setProperty_0(n,IN_LAYER_CONSTRAINT,v.constraint==='TOP'?TOP_1:v.constraint==='BOTTOM'?BOTTOM_0:NONE_6);$setLayer_0(n,l);});});
  const size=g.size_0,offset=g.offset,layerList=g.layers,saved=$getProperty;let reads=0,first=null,same=true;
  $getProperty=function(holder,prop){const value=saved(holder,prop);if(holder===g&&prop===SPACING_PORTS_SURROUNDING){reads++;if(first===null)first=value;else same=same&&first===value;}return value;};
  const monitor={begin:(name,total)=>events.push({kind:'begin',name,total}),done_1:()=>events.push({kind:'done'})};
  try{$process_21(g,monitor);$process_33(g,monitor);}finally{$getProperty=saved;}
  const has=$hasProperty(g,SPACING_PORTS_SURROUNDING),margin=has?saved(g,SPACING_PORTS_SURROUNDING):null;
  return {id:item.id,events,rows:layers.map((l,i)=>({nodes:l.nodes.array.map(n=>names.get(n)),size:[l.size_0.x_0,l.size_0.y_0],sameList:l.nodes===rows[i],sameSize:l.size_0===initial[i],sameLayerPointers:l.nodes.array.every(n=>n.layer===l)})),height:g.size_0.y_0,offsetY:g.offset.y_0,sameGraphObjects:g.size_0===size&&g.offset===offset&&g.layers===layerList,surrounding:{reads,has,value:margin?[margin.top_0,margin.right,margin.bottom,margin.left]:null,sameReadReference:same,explicitReferencePreserved:explicit===null?null:margin===explicit}};
 }),layoutExecuted:false,workingGraphPhaseExecuted:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__simpleLayerProcessors(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-simple-layer-processors/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
