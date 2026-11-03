// Development oracle. One request, one process, verified immutable npm artifact.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
const errorRecord = error => ({ name: String(error.name || 'Error'), message: String(error.message || error) });

async function main() {
  const [packagePath, requestPath, outputPath] = process.argv.slice(2);
  if (!packagePath || !requestPath || !outputPath) throw new Error('Usage: node capture_layout.cjs PACKAGE REQUEST NEW_OUTPUT');
  const packageRoot = path.resolve(packagePath);
  const lock = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../UPSTREAM.json'), 'utf8'));
  // Verify every shipped file used or reachable by this package, not just its version.
  for (const [name, sha] of Object.entries(lock.distribution.sha256Files)) {
    if (digest(fs.readFileSync(path.join(packageRoot, name))) !== sha) throw new Error('Locked npm SHA differs: ' + name);
  }
  const bytes = fs.readFileSync(requestPath);
  const request = JSON.parse(bytes.toString('utf8'));
  if (request.schema !== 'py-elk-layout-request/v1') throw new Error('Invalid request schema');
  const constructorOptions = clone(request.constructor);
  const graph = clone(request.graph);
  const layoutArguments = clone(request.layoutArguments);
  const ELK = require(path.join(packageRoot, 'lib/elk.bundled.js'));
  let elk;
  const observation = { schema: 'py-elk-layout-observation/v1', requestSha256: digest(bytes),
    engine: { name: 'elkjs', version: lock.javascript.version, node: process.version, platform: process.platform,
      arch: process.arch, entrypoint: 'lib/elk.bundled.js',
      entrypointSha256: lock.distribution.sha256Files['lib/elk.bundled.js'] } };
  try {
    elk = new ELK(constructorOptions);
    observation.result = await elk.layout(graph, layoutArguments);
    observation.outcome = 'returned';
  } catch (error) {
    observation.outcome = 'threw';
    observation.error = errorRecord(error);
    // Original stack is diagnostic, not an API message or coordinate field.
    observation.diagnostics = { errorStack: String(error.stack || error) };
  }
  observation.inputAfter = graph;
  observation.constructorAfter = constructorOptions;
  observation.argumentsAfter = layoutArguments;
  if (elk) {
    try {
      const returned = elk.terminateWorker();
      observation.termination = { outcome: 'returned', returnKind: typeof returned };
    } catch (error) {
      observation.termination = { outcome: 'threw', ...errorRecord(error) };
    }
  } else {
    observation.termination = { outcome: 'notConstructed' };
  }
  fs.writeFileSync(outputPath, JSON.stringify(observation, null, 2) + '\n', { flag: 'wx' });
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 2; });
