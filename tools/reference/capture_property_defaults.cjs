// Development-only owner-specific Property defaults; never runs a layout.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto'), Module = require('node:module');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const [packageArg, outputArg] = process.argv.slice(2);
if (!packageArg || !outputArg) throw Error('Usage: node capture_property_defaults.cjs ELKJS_PACKAGE NEW_OUTPUT');
const packagePath = path.resolve(packageArg), workerPath = path.join(packagePath, 'lib/elk-worker.js');
const bytes = fs.readFileSync(workerPath), source = bytes.toString('utf8');
if (sha(bytes) !== '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86') throw Error('Worker differs');
const owners = ['CoreOptions', 'BoxLayouterOptions', 'FixedLayouterOptions', 'RandomLayouterOptions',
  'LayeredMetaDataProvider', 'LayeredOptions', 'ForceMetaDataProvider', 'ForceOptions',
  'StressMetaDataProvider', 'StressOptions', 'MrTreeMetaDataProvider', 'MrTreeOptions',
  'RadialMetaDataProvider', 'RadialOptions', 'DisCoMetaDataProvider', 'DisCoOptions', 'PolyominoOptions',
  'SporeMetaDataProvider', 'SporeOverlapRemovalOptions', 'SporeCompactionOptions',
  'RectPackingMetaDataProvider', 'RectPackingOptions'];
const spans = [], ownerCalls = [];
for (const owner of owners) {
  // Fixed generated functions have a top-level closing brace on its own line.
  const start = source.indexOf('function $clinit_' + owner + '(){');
  if (start < 0) throw Error('Missing owner ' + owner);
  const end = source.indexOf('\n}', start) + 2;
  if (end < start) throw Error('Missing owner end ' + owner);
  const body = source.slice(start, end);
  const names = [...body.matchAll(/^  ([A-Za-z_$][A-Za-z0-9_$]*) = (?!=)/gm)]
    .map(match => match[1]).filter(name => !name.startsWith('$clinit_'));
  spans.push({owner, startLine: source.slice(0, start).split('\n').length,
    endLine: source.slice(0, end).split('\n').length, sha256: sha(Buffer.from(body)), sourceBytesBase64: Buffer.from(body).toString('base64')});
  ownerCalls.push(`owner(${JSON.stringify(owner)},()=>{$clinit_${owner}();return [${names.map(name => `[${JSON.stringify(name)},${name}]`).join(',')}];});`);
}
const bridge = `
global.__propertyDefaultObservation=function(){
 registerLayoutAlgorithms(['layered','force','stress','mrtree','radial','disco','sporeOverlap','sporeCompaction','rectpacking']);
 const result=[], identities=new Map(); let nextIdentity=1;
 const identity=v=>{if(v===null||(typeof v!=='object'&&typeof v!=='function'))return null;
  if(!identities.has(v))identities.set(v,nextIdentity++);return identities.get(v);};
 const list=x=>{const a=[],it=x.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 function value(v){
  if(v==null)return null;
  if(typeof v==='number')return Number.isFinite(v)?(Object.is(v,-0)?{negativeZero:true}:v):{nonfinite:String(v)};
  if(typeof v==='boolean'||typeof v==='string')return v;
  if(typeof v.name_0==='string')return {enum:v.name_0};
  if(typeof v.value_0==='number'||typeof v.value_0==='boolean'||typeof v.value_0==='string')return value(v.value_0);
  if('x_0'in v&&'y_0'in v)return {vector:[value(v.x_0),value(v.y_0)]};
  if('top_0'in v)return {insets:[value(v.top_0),value(v.right),value(v.bottom),value(v.left)]};
  if(typeof v.iterator_0==='function')return {sequence:list(v).map(value)};
  return {unmappedDefault:true};
 }
 function owner(name,get){
  const properties=[];
  for(const [symbol,p] of get()){
   if(p==null||!instanceOf(p,153))continue;
   properties.push({symbol,id:p.getId(),declaredDefault:value(p.defaultValue),
    propertyIdentity:identity(p),defaultIdentity:identity(p.defaultValue),
    sourceCloneableDefault:p.defaultValue!=null&&instanceOf(p.defaultValue,4)});
  }
  result.push({owner:name,properties});
 }
 ${ownerCalls.join('\n')}
 return result;
};`;
const workerModule = new Module(workerPath, module); workerModule.filename = workerPath;
workerModule.paths = Module._nodeModulePaths(packagePath); workerModule._compile(source + bridge, workerPath);
const observed = global.__propertyDefaultObservation();
fs.writeFileSync(outputArg, JSON.stringify({schema: 'py-elk-original-owner-property-defaults/v1',
  workerSha256: sha(bytes), probeSha256: sha(fs.readFileSync(__filename)), pid: process.pid, parentPid: process.ppid,
  node: process.version, owners: observed, sourceSpans: spans, layoutExecuted: false,
  candidateExecuted: false, fullValidation: false,
  scope: 'Actual static Property owners/defaults/identity; provider aliases and overrides are separate from metadata defaults'}, null, 2) + '\n', {flag: 'wx'});
