// Original P02/P02S local primitives over typed field/list/property scaffolding.
// No Python implementation or candidate output defines these expected values.
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [workerPath,initPath,orderPath,sortPath,requestPath,outPath]=process.argv.slice(2);
const worker=fs.readFileSync(workerPath),lines=worker.toString().split(/\r?\n/);
const sourcePaths=[initPath,orderPath,sortPath],sources=sourcePaths.map(p=>JSON.parse(fs.readFileSync(p)));
if(sha(worker)!==sources[0].fixedSource.sha256)throw Error('Original worker SHA differs');
const initSpans=sources[0].components[0].spans.filter(s=>['$setSide','$isSideFixed'].includes(s.symbol));
const orderSpans=sources[1].spans.filter(s=>!['$clinit_PortListSorter','IN_EDGES and OUT_EDGES lambda dispatch'].includes(s.symbol));
const spans=[...initSpans,...orderSpans,...sources[2].spans];
for(const s of spans){const b=Buffer.from(lines.slice(s.startLine-1,s.endLine).join('\n')+'\n');if(sha(b)!==s.sha256||!b.equals(Buffer.from(s.sourceBytesBase64,'base64')))throw Error('Original span differs');}
const list=array=>({array,iterator_0(){let i=0;return {hasNext_0(){return i<array.length;},next_1(){return array[i++];}};}});
const requestRaw=fs.readFileSync(requestPath),rows=[];
for(const input of JSON.parse(requestRaw).cases){
 const sides=Object.fromEntries(['UNDEFINED','NORTH','EAST','SOUTH','WEST'].map((name,ordinal)=>[name,{name,ordinal}]));
 const constraints=Object.fromEntries(['UNDEFINED','FREE','FIXED_SIDE','FIXED_ORDER','FIXED_RATIO','FIXED_POS'].map((name,ordinal)=>[name,{name,ordinal}]));
 const c={_: {},$clinit_PortSide(){},$clinit_PortConstraints(){},$clinit_Collections(){},$clinit_LayeredOptions(){},$clinit_InternalProperties_1(){},$clinit_PortSortingStrategy(){},$clinit_PortListSorter(){},$clinit_Comparators(){},
  UNDEFINED_5:sides.UNDEFINED,NORTH_3:sides.NORTH,EAST_2:sides.EAST,SOUTH_2:sides.SOUTH,WEST_2:sides.WEST,
  UNDEFINED_4:constraints.UNDEFINED,FREE:constraints.FREE,FIXED_SIDE:constraints.FIXED_SIDE,FIXED_ORDER:constraints.FIXED_ORDER,FIXED_RATIO:constraints.FIXED_RATIO,FIXED_POS:constraints.FIXED_POS,
  PORT_CONSTRAINTS_0:'PORT_CONSTRAINTS',PORT_INDEX:'PORT_INDEX',PORT_DUMMY:'PORT_DUMMY',EXT_PORT_SIDE:'EXT_PORT_SIDE',REVERSED:'REVERSED',PORT_SORTING_STRATEGY_0:'PORT_SORTING_STRATEGY',PORT_DEGREE:{},
  castTo(x){return x;},castToBoolean(x){return x;},$booleanValue(x){return x;},$getProperty(x,key){return x.properties[key];},$setProperty_0(x,key,v){x.properties[key]=v;},
  checkCriticalElementIndex(){},checkCriticalArrayBounds_0(){},checkNotNull(x){return x;},setCheck(a,i,v){a[i]=v;},$set_1(a,i,v){a.array[i]=v;},$get_11(a,i){return a.array[i];},
  valueOf_3(value_0){return {value_0};},Pair:function(first,second){this.first=first;this.second=second;},EnumMap:function(){this.data={};},$put_7(map,key,value){map.data[key.name]=value;},
  Lorg_eclipse_elk_core_options_PortSide_2_classLit:{},ArrayList$1:function(value){this.i=0;this.this$01=value;},$next_6(iterator){return iterator.this$01.array[iterator.i++];},
  toJs(x){return x;},IllegalStateException_0:Error,NullPointerException:Error,isNaN,emptyMethod(){},PortSortingStrategy:function(name,ordinal){this.name=name;this.ordinal=ordinal;}};
 vm.createContext(c);vm.runInContext(spans.map(s=>Buffer.from(s.sourceBytesBase64,'base64').toString()).join('\n'),c);
 c.$clinit_PortSortingStrategy();
 c.CMP_COMBINED=c._;c.CMP_PORT_SIDE={compare_1:c.lambda$0_26};c.CMP_PORT_DEGREE_EAST_WEST={compare_1:c.lambda$4_5};c.IN_EDGES={apply_0:p=>p.incomingEdges};c.OUT_EDGES={apply_0:p=>p.outgoingEdges};
 const node={properties:{PORT_CONSTRAINTS:constraints[input.constraints]},ports:null};
 const ports=input.ports.map(p=>{const properties={};if('index' in p)properties.PORT_INDEX={value_0:p.index};if(p.dummySide)properties.PORT_DUMMY={properties:{EXT_PORT_SIDE:sides[p.dummySide]}};
  return {id:p.id,owner:node,properties,side:sides[p.side],pos:{x_0:p.position[0],y_0:p.position[1]},size_0:{x_0:0,y_0:0},anchor:{x_0:0,y_0:0},explicitlySuppliedPortAnchor:false,
   incomingEdges:list((p.incoming||[]).map(v=>({properties:{REVERSED:v}}))),outgoingEdges:list((p.outgoing||[]).map(v=>({properties:{REVERSED:v}})))};});
 node.ports=list(ports);const graph={layerlessNodes:list(input.layerless?[node]:[]),layers:list(input.layerless?[]:[{nodes:list([node])}]),properties:{PORT_SORTING_STRATEGY:input.strategy==='PORT_DEGREE'?c.PORT_DEGREE:{}}};
 const monitor={begin(){},done_1(){}};if(input.processSides)c.$process_44(graph,monitor);c.$process_43(graph,monitor);
 const ranges={};if(node.portSideIndices)for(const [key,pair] of Object.entries(node.portSideIndices.data))ranges[key]=[pair.first.value_0,pair.second.value_0];
 rows.push({id:input.id,portOrder:ports.map(p=>p.id),sides:ports.map(p=>p.side.name),constraints:node.properties.PORT_CONSTRAINTS.name,cached:node.portSidesCached===true,ranges});
}
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-port-order-observation/v1',mode:'original-local-primitives',node:process.version,pid:process.pid,parentPid:process.ppid,workerSha256:sha(worker),sourceFilesSha256:Object.fromEntries(sourcePaths.map(p=>[p,sha(fs.readFileSync(p))])),requestSha256:sha(requestRaw),cases:rows,publicLayoutExecuted:false,candidateExecuted:false},null,2)+'\n',{flag:'wx'});
