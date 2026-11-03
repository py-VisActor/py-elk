// Development-only metadata capture from the separately verified elkjs artifact.
// This does not execute or provide a Python layout implementation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

async function main() {
  const [packagePath, outputPath] = process.argv.slice(2);
  if (!packagePath || !outputPath) throw new Error('Usage: node capture_metadata.cjs PACKAGE_DIRECTORY NEW_OUTPUT_DIRECTORY');
  const packageRoot = path.resolve(packagePath);
  const out = path.resolve(outputPath);
  const metadata = JSON.parse(fs.readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));
  if (metadata.name !== 'elkjs' || metadata.version !== '0.12.1') throw new Error('Expected the locked elkjs@0.12.1 artifact');
  const lock = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../UPSTREAM.json'), 'utf8'));
  for (const name of ['package.json', 'lib/elk.bundled.js']) {
    const sha = crypto.createHash('sha256').update(fs.readFileSync(path.join(packageRoot, name))).digest('hex');
    if (sha !== lock.distribution.sha256Files[name]) throw new Error('Locked npm file hash differs: ' + name);
  }
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.mkdirSync(out, { recursive: false });
  const ELK = require(path.join(packageRoot, 'lib/elk.bundled.js'));
  const elk = new ELK();
  {
    const queries = [
      ['algorithms', () => elk.knownLayoutAlgorithms()],
      ['options', () => elk.knownLayoutOptions()],
      ['categories', () => elk.knownLayoutCategories()],
    ];
    const files = {};
    const counts = {};
    for (const [name, query] of queries) {
      const values = await query();
      const bytes = Buffer.from(JSON.stringify(values, null, 2) + '\n');
      fs.writeFileSync(path.join(out, name + '.json'), bytes, { flag: 'wx' });
      files[name + '.json'] = crypto.createHash('sha256').update(bytes).digest('hex');
      counts[name] = values.length;
    }
    const entry = fs.readFileSync(path.join(packageRoot, 'lib/elk.bundled.js'));
    let termination;
    try {
      elk.terminateWorker();
      termination = { operation: 'terminateWorker', outcome: 'returned' };
    } catch (error) {
      if (!(error instanceof TypeError) || error.message !== 'this.worker.terminate is not a function') throw error;
      termination = { operation: 'terminateWorker', outcome: 'throws', name: error.name, message: error.message };
    }
    const report = { schema: 'py-elk-metadata-capture/v1', status: 'OFFICIAL_METADATA_CAPTURED',
      package: 'elkjs', version: metadata.version, entrypoint: 'lib/elk.bundled.js',
      entrypointSha256: crypto.createHash('sha256').update(entry).digest('hex'),
      node: process.version, platform: process.platform, arch: process.arch, counts, files,
      pythonAlgorithmsVerified: 0, layoutFixturesCaptured: 0, contractObservations: [termination],
      limitation: 'Default-registration metadata only. No Python API, algorithm, coordinates, or layout oracle acceptance.' };
    fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
    process.stdout.write(JSON.stringify(report, null, 2) + '\n');
  }
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1; });
