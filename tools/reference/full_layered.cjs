// Public stock-elkjs batch capture. No candidate imports or normalization.
// Shared observation contract: capture_e09_layout.cjs.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));

async function main() {
  const [packagePath, manifestPath] = process.argv.slice(2);
  if (!packagePath || !manifestPath) throw Error('Usage: PACKAGE BATCH_MANIFEST');
  const lock = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../UPSTREAM.json'), 'utf8'));
  const root = path.resolve(packagePath);
  for (const [name, sha] of Object.entries(lock.distribution.sha256Files)) {
    if (digest(fs.readFileSync(path.join(root, name))) !== sha) throw Error('Locked npm SHA differs: ' + name);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const ELK = require(path.join(root, 'lib/elk.bundled.js'));
  for (const row of manifest.cases) {
    const raw = fs.readFileSync(row.request), request = JSON.parse(raw);
    const graph = clone(request.graph), options = clone(request.constructor), args = clone(request.layoutArguments);
    const observation = {schema:'py-elk-layout-observation/v1', requestSha256:digest(raw),
      engine:{name:'elkjs',version:lock.javascript.version,node:process.version,platform:process.platform,
        arch:process.arch,pid:process.pid,executable:process.execPath,
        executableSha256:digest(fs.readFileSync(process.execPath)),entrypoint:'lib/elk.bundled.js',
        entrypointSha256:lock.distribution.sha256Files['lib/elk.bundled.js']},
      inputBefore:clone(graph),constructorBefore:clone(options),argumentsBefore:clone(args),clock:{startMs:Date.now()}};
    let elk;
    try {
      elk = new ELK(options);
      observation.result = await elk.layout(graph,args);
      observation.outcome = 'returned';
    } catch(error) {
      observation.outcome = 'threw';
      observation.error = {name:String(error.name || 'Error'),message:String(error.message || error)};
      observation.diagnostics = {errorStack:String(error.stack || error)};
    }
    observation.clock.endMs = Date.now();
    observation.inputAfter = graph;
    observation.constructorAfter = options;
    observation.argumentsAfter = args;
    if(elk) {
      try { const value=elk.terminateWorker(); observation.termination={outcome:'returned',returnKind:typeof value}; }
      catch(error) { observation.termination={outcome:'threw',name:String(error.name || 'Error'),message:String(error.message || error)}; }
    } else observation.termination={outcome:'notConstructed'};
    fs.writeFileSync(row.output,JSON.stringify(observation,null,2)+'\n',{flag:'wx'});
    process.stdout.write(JSON.stringify({id:row.id,outcome:observation.outcome})+'\n');
  }
}
main().catch(error=>{process.stderr.write(String(error.stack || error)+'\n');process.exitCode=2;});
