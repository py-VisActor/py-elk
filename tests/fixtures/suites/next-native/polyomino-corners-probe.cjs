// Actual original DCPolyomino objects passed to the original comparator only.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__cornerCases=function(cases){
 $clinit_DCDirection();$clinit_Direction();const dirs={NORTH:NORTH_0,EAST:EAST_0,SOUTH:SOUTH_0,WEST:WEST_0};
 function poly(names){
  const outline=new LinkedList;[[0,0],[4,0],[4,4],[0,4]].forEach(v=>$add_7(outline,new KVector_1(...v)));
  const element=new DCElement(outline);names.forEach(name=>new DCExtension(element,dirs[name],new KVector_1(2,2),1));
  const component=new DCComponent,elements=new ArrayList;$add_3(elements,element);$addElements(component,elements);
  return new DCPolyomino(component,1,1);
 }
 const comparator=new PolyominoCompactor$CornerCasesGreaterThanRestComparator;
 return cases.map(c=>{
  const first=poly(c.first),second=poly(c.second),row={id:c.id,firstActualDirections:first.polyominoExtensions.array.map(x=>x.first.name_0),
   secondActualDirections:second.polyominoExtensions.array.map(x=>x.first.name_0)};
  try{row.outcome='returned';row.value=comparator.compare_1(first,second);}
  catch(e){row.outcome='threw';row.error={name:String(e.name),message:String(e.message),text:String(e),stack:String(e.stack)};}
  return row;
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const cases=global.__cornerCases(JSON.parse(requestBytes).cases);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),
 pid:process.pid,parentPid:process.ppid,node:process.version,cases,candidateExecuted:false,layoutExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
