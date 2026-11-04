// Real EndLabelSorter over explicitly prepared actual LabelCells/adapters.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const[pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),wp=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(wp),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__endLabelSorter=function(s){
 getInstance();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_EdgeLabelPlacement();$clinit_EndLabelSorter();
 const g=new LGraph,nodes={},ports={},edges={},labels={},cells=[],events=[],initializations=[];
 const layers=[new Layer(g),new Layer(g)];layers.forEach(l=>$add_3(g.layers,l));
 for(const v of s.nodes){const n=nodes[v.id]=new LNode(g);$setLayer_0(n,layers[v.layer]);n.id_0=99;for(const p of v.ports){const port=ports[p]=new LPort;$setSide(port,v.id==='b'?WEST_2:EAST_2);$setNode(port,n);port.id_0=99;}}
 for(const[id,a,b]of s.edges){const e=edges[id]=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 for(const[id,e,placement]of s.labels){const l=labels[id]=new LLabel_0(id);$setProperty_0(l,EDGE_LABELS_PLACEMENT,placement==='HEAD'?HEAD:TAIL);$setProperty_0(l,END_LABEL_EDGE,edges[e]);$add_3(edges[e].labels,l);}
 for(const c of s.cells){const cell=new LabelCell(0),map=$hasProperty(nodes[c.node],END_LABELS_0)?$getProperty(nodes[c.node],END_LABELS_0):new HashMap;for(const id of c.labels)$add_3(cell.labels,new LGraphAdapters$LLabelAdapter(labels[id]));$put_6(map,ports[c.port],cell);$setProperty_0(nodes[c.node],END_LABELS_0,map);cells.push([c,cell,cell.labels,cell.labels.array.slice()]);}
 const old=$initialize_2;$initialize_2=function(graph){initializations.push(graph===g);return old(graph);};
 try{$process_10(g,{begin:(name,total)=>events.push({kind:'begin',name,total}),done_1:()=>events.push({kind:'done'})});}finally{$initialize_2=old;}
 return{events,initializations,cells:cells.map(([spec,cell,list,refs])=>({port:spec.port,labels:cell.labels.array.map(a=>a.element.text_0),sameList:cell.labels===list,sameAdapters:cell.labels.array.every(a=>refs.includes(a))})),ids:s.nodes.map(v=>({node:v.id,id:nodes[v.id].id_0,ports:v.ports.map(p=>({port:p,id:ports[p].id_0}))})),edgeLabels:s.edges.map(([id])=>({edge:id,labels:edges[id].labels.array.map(l=>l.text_0)})),geometry:s.labels.map(([id])=>({label:id,x:labels[id].pos.x_0,y:labels[id].pos.y_0,width:labels[id].size_0.x_0,height:labels[id].size_0.y_0})),preparedCells:true,layoutExecuted:false};
};`;
const m=new Module(wp,module);m.filename=wp;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,wp);
const observation=global.__endLabelSorter(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-end-label-sorter/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
