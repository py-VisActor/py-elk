// E09 development oracle: original bytes, one real layout, integer wall ticks.
// No candidate module or normalization is reachable from this collector.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const digest = raw => crypto.createHash('sha256').update(raw).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
async function main() {
  const [packagePath, requestPath, outputPath] = process.argv.slice(2);
  if (!packagePath || !requestPath || !outputPath) throw Error('Usage: PACKAGE REQUEST NEW_OUTPUT');
  const lock = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../UPSTREAM.json'), 'utf8'));
  const packageRoot = path.resolve(packagePath);
  for (const [name, sha] of Object.entries(lock.distribution.sha256Files)) {
    if (digest(fs.readFileSync(path.join(packageRoot, name))) !== sha) throw Error('Locked npm SHA differs: ' + name);
  }
  const raw = fs.readFileSync(requestPath), request = JSON.parse(raw);
  if (request.schema !== 'py-elk-layout-request/v1') throw Error('Invalid request schema');
  const options = clone(request.constructor), graph = clone(request.graph), args = clone(request.layoutArguments);
  const ELK = require(path.join(packageRoot, 'lib/elk.bundled.js'));
  const observation = {schema:'py-elk-layout-observation/v1', requestSha256:digest(raw),
    engine:{name:'elkjs',version:lock.javascript.version,node:process.version,platform:process.platform,arch:process.arch,
      executable:process.execPath, executableSha256:digest(fs.readFileSync(process.execPath)),pid:process.pid,
      entrypoint:'lib/elk.bundled.js',entrypointSha256:lock.distribution.sha256Files['lib/elk.bundled.js']},
    inputBefore:clone(graph),constructorBefore:clone(options),argumentsBefore:clone(args)};
  let elk;
  observation.clock={startMs:Date.now()};
  try {
    elk = new ELK(options);
    observation.result = await elk.layout(graph,args);
    observation.outcome = 'returned';
  } catch (error) {
    observation.outcome='threw';
    observation.error={name:String(error.name || 'Error'),message:String(error.message || error)};
    observation.diagnostics={errorStack:String(error.stack || error)};
  }
  observation.clock.endMs=Date.now();
  observation.inputAfter=graph; observation.constructorAfter=options; observation.argumentsAfter=args;
  if (elk) {
    try { const value=elk.terminateWorker(); observation.termination={outcome:'returned',returnKind:typeof value}; }
    catch(error) {observation.termination={outcome:'threw',name:String(error.name || 'Error'),message:String(error.message || error)};}
  } else observation.termination={outcome:'notConstructed'};
  fs.writeFileSync(outputPath,JSON.stringify(observation,null,2)+'\n',{flag:'wx'});
}
main().catch(error=>{process.stderr.write(String(error.stack || error)+'\n');process.exitCode=2;});
