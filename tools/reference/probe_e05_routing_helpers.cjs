// B independent in-memory original generated helpers, never a layout fixture.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const ROOT=path.resolve(__dirname,'../..');
const [pkgArg,outArg]=process.argv.slice(2);if(!pkgArg||!outArg)throw Error('PACKAGE NEW_JSON required');
const pkg=path.resolve(pkgArg),file=path.join(pkg,'lib/elk-worker.js'),bytes=fs.readFileSync(file);
const sha=v=>crypto.createHash('sha256').update(v).digest('hex');
const lock=JSON.parse(fs.readFileSync(path.join(ROOT,'UPSTREAM.json'),'utf8'));
for(const [name,expected] of Object.entries(lock.distribution.sha256Files))if(sha(fs.readFileSync(path.join(pkg,name)))!==expected)throw Error('SHA drift '+name);
const bridge=String.raw`
module.exports.__E05RoutingHelperBridge={
  run: function(input){
    const make=row=>{const value=new HyperEdgeSegment(null);for(const x of row.incoming)$add_7(value.incomingConnectionCoordinates,x);for(const x of row.outgoing)$add_7(value.outgoingConnectionCoordinates,x);$recomputeExtent(value);return value;};
    const source=make(input.segment),causing=make(input.causing);source.splitBy=causing;
    const others=input.others.map(make);
    for(let i=0;i<others.length;i++){new HyperEdgeSegmentDependency(($clinit_HyperEdgeSegmentDependency$DependencyType(),REGULAR),i%2?source:others[i],i%2?others[i]:source,1);}
    const areas=new ArrayList;for(const x of input.areas)areas.array.push(new HyperEdgeSegmentSplitter$FreeArea(x[0],x[1]));
    const split=new HyperEdgeSegment(null),partner=new HyperEdgeSegment(null);
    $addAll(split.incomingConnectionCoordinates,source.incomingConnectionCoordinates);split.splitBy=causing;split.splitPartner=partner;$recomputeExtent(split);
    $addAll(partner.outgoingConnectionCoordinates,source.outgoingConnectionCoordinates);partner.splitPartner=split;$recomputeExtent(partner);
    const ratings=[];for(const area of areas.array){const r=$rateArea(source,split,partner,area);ratings.push([r.dependencies,r.crossings]);}
    const chosen=$chooseBestAreaIndex(source,areas,0,areas.array.length-1);
    const position=$computePositionToSplitAndUpdateFreeAreas(source,areas,input.threshold);
    return {ratings,chosen,position,remainingAreas:areas.array.map(a=>[a.startPosition,a.endPosition]),extent:[source.startPosition,source.endPosition]};
  }
};
`;
const compiled=new Module(file,module);compiled.filename=file;compiled.paths=Module._nodeModulePaths(pkg);compiled._compile(bytes.toString('utf8')+bridge,file);
const api=compiled.exports.__E05RoutingHelperBridge;
const records=[];
for(let index=0;index<24;index++){
  const a=(index%3)*.1-10,b=(index%4)*2+1;
  const input={segment:{incoming:[a],outgoing:[b]},causing:{incoming:[b-.01],outgoing:[a+.02]},
    others:[{incoming:[a-3],outgoing:[b+4]},{incoming:[a+5],outgoing:[b-3]},{incoming:[b],outgoing:[a]}],
    areas:[[-50,-40],[a-.1,a+.1],[(a+b)/2-.001,(a+b)/2+.001],[b-1,b+1],[40,50]],threshold:index%2?.2:0};
  records.push({input,result:api.run(input)});
}
const report={schema:'py-elk-e05-routing-original-helper-observations/v1',workerSha256:sha(bytes),instrumentedSourceSha256:sha(Buffer.from(bytes.toString('utf8')+bridge)),toolSha256:sha(fs.readFileSync(__filename)),memoryOnlyBridge:bridge,records,
  classification:'Explicit synthetic original-helper prerequisites, not a public-request capture or end-to-end layout acceptance'};
fs.writeFileSync(path.resolve(outArg),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({cases:records.length}));
