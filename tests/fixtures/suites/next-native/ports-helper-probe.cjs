// Local primitive oracle: original worker functions, not public layout execution.
// The typed graph/property scaffolding below supplies only fields read/written
// by the approved P01 closure; it implements no port-placement arithmetic.
const fs=require('node:fs'), vm=require('node:vm'), crypto=require('node:crypto');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [workerPath,proposalPath,requestPath,outPath]=process.argv.slice(2);
const worker=fs.readFileSync(workerPath), proposalRaw=fs.readFileSync(proposalPath);
const proposal=JSON.parse(proposalRaw), requestRaw=fs.readFileSync(requestPath);
if(sha(worker)!==proposal.fixedSource.sha256)throw Error('Fixed worker SHA differs');
const lines=worker.toString().split(/\r?\n/), functions=['calcPortOffset','calcPortSide','initializePort','$setSide'];
const spans=proposal.components[0].spans.filter(s=>functions.includes(s.symbol));
for(const s of spans){const raw=Buffer.from(lines.slice(s.startLine-1,s.endLine).join('\n')+'\n');if(sha(raw)!==s.sha256||!raw.equals(Buffer.from(s.sourceBytesBase64,'base64')))throw Error('Original function bytes differ');}
const rows=[];
for(const input of JSON.parse(requestRaw).cases){
 const sideNames=['UNDEFINED','NORTH','EAST','SOUTH','WEST'];
 const side=Object.fromEntries(sideNames.map((name,ordinal)=>[name,{name,ordinal}]));
 const constraint=Object.fromEntries(['UNDEFINED','FREE','FIXED_SIDE','FIXED_ORDER','FIXED_RATIO','FIXED_POS'].map((name,ordinal)=>[name,{name,ordinal}]));
 const props={...input.properties};
 const context={$clinit_PortSide(){},$clinit_PortConstraints(){},$clinit_Collections(){},$clinit_LayeredOptions(){},$clinit_InternalProperties_1(){},
  UNDEFINED_5:side.UNDEFINED,NORTH_3:side.NORTH,EAST_2:side.EAST,SOUTH_2:side.SOUTH,WEST_2:side.WEST,
  UNDEFINED_4:constraint.UNDEFINED,FREE:constraint.FREE,FIXED_RATIO:constraint.FIXED_RATIO,
  PORT_BORDER_OFFSET:'PORT_BORDER_OFFSET',PORT_RATIO_OR_POSITION_0:'PORT_RATIO_OR_POSITION',
  EMPTY_MAP:{containsKey(){return false;}},$setProperty_0(port,key,value){props[key]=value;},
  toJs(e){return e;},NullPointerException:Error};
 vm.createContext(context);vm.runInContext(spans.map(s=>Buffer.from(s.sourceBytesBase64,'base64').toString()).join('\n'),context);
 const port={side:side[input.side],owner:{size_0:{x_0:input.nodeSize[0],y_0:input.nodeSize[1]}},
  pos:{x_0:input.position[0],y_0:input.position[1]},size_0:{x_0:input.portSize[0],y_0:input.portSize[1]},
  anchor:{x_0:input.anchor[0],y_0:input.anchor[1]},explicitlySuppliedPortAnchor:false,
  propertyMap:{containsKey(key){return Object.prototype.hasOwnProperty.call(props,key);}}};
 const direction={ordinal:['UNDEFINED','RIGHT','LEFT','DOWN','UP'].indexOf(input.direction)};
 const inferredSide=context.calcPortSide(port,direction).name;
 context.initializePort(port,constraint[input.constraints],direction,input.explicitAnchor?{x_0:input.explicitAnchor[0],y_0:input.explicitAnchor[1]}:null);
 if(input.sideAfter)context.$setSide(port,side[input.sideAfter]);
 rows.push({id:input.id,inferredSide,side:port.side.name,anchor:[port.anchor.x_0,port.anchor.y_0],properties:props,explicitlySuppliedPortAnchor:port.explicitlySuppliedPortAnchor});
}
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-port-helper-observation/v1',mode:'original-local-primitive',node:process.version,pid:process.pid,parentPid:process.ppid,workerSha256:sha(worker),proposalSha256:sha(proposalRaw),requestSha256:sha(requestRaw),cases:rows,publicLayoutExecuted:false,candidateExecuted:false},null,2)+'\n',{flag:'wx'});
