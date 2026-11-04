// Development-only contract probes. Each probe is a fresh process/ELK instance.
// All raw requests, actual argument forms, snapshots, errors and failed exits survive.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
const value = v => ({ kind: 'value', value: v });
const omitted = () => ({ kind: 'omitted' });
const undef = () => ({ kind: 'undefined' });
const snapshot = v => v === undefined ? { kind: 'undefined' } : value(clone(v));
const errorRecord = e => ({ name: String(e.name || 'Error'), message: String(e.message || e), stack: String(e.stack || e) });
const ROOT = path.resolve(__dirname, '../..');

function graph() {
  return { id: 'root', layoutOptions: { 'elk.algorithm': 'layered', 'elk.randomSeed': 7 },
    children: [{ id: 'a', width: 40, height: 30 }, { id: 'b', width: 40, height: 30 }],
    edges: [{ id: 'e0', sources: ['a'], targets: ['b'] }] };
}

function catalogue() {
  const probes = [];
  const add = (id, category, constructor = omitted(), g = graph(), calls = null) => {
    probes.push({ id, category, constructor, graphs: { g: value(g) }, calls: calls || [{ id: 'layout-1', method: 'layout', graphKey: 'g', arguments: omitted() }] });
  };
  const forms = [['omitted', omitted()], ['undefined', undef()], ['empty-object', value({})],
    ['null', value(null)], ['false', value(false)], ['zero', value(0)], ['empty-string', value('')]];
  for (const [name, form] of forms) add('constructor-' + name, 'constructor-argument', form);
  for (const [name, form] of forms.slice(1)) {
    add('constructor-default-options-' + name, 'constructor-default-layout-options', value({ defaultLayoutOptions: name === 'undefined' ? undefined : form.value }));
    if (name === 'undefined') probes.at(-1).constructorUndefinedFields = ['defaultLayoutOptions'];
  }
  for (const [name, form] of forms) add('layout-arguments-' + name, 'layout-argument', omitted(), graph(), [{ id: 'layout-1', method: 'layout', graphKey: 'g', arguments: form }]);
  for (const [name, form] of forms.slice(1)) {
    const args = { layoutOptions: name === 'undefined' ? undefined : form.value };
    // Undefined is represented in a separate derived-argument descriptor.
    add('layout-options-' + name, 'layout-options', value({ defaultLayoutOptions: { 'elk.direction': 'DOWN' } }), graph(),
      [{ id: 'layout-1', method: 'layout', graphKey: 'g', arguments: value(args), undefinedFields: name === 'undefined' ? ['layoutOptions'] : [] }]);
  }
  for (const [name, form] of forms.slice(1)) {
    const probe = { id: 'graph-' + name, category: 'graph-argument', constructor: omitted(), graphs: { g: form },
      calls: [{ id: 'layout-1', method: 'layout', graphKey: 'g', arguments: omitted() }] };
    probes.push(probe);
  }
  probes.push({ id: 'graph-omitted', category: 'graph-argument', constructor: omitted(), graphs: {}, calls: [{ id: 'layout-1', method: 'layout', graphKey: null, arguments: omitted() }] });
  add('precedence-constructor-default', 'option-precedence', value({ defaultLayoutOptions: { 'elk.direction': 'DOWN' } }));
  add('precedence-empty-call-replaces', 'option-precedence', value({ defaultLayoutOptions: { 'elk.direction': 'DOWN' } }), graph(), [{ id: 'layout-1', method: 'layout', graphKey: 'g', arguments: value({ layoutOptions: {} }) }]);
  add('precedence-call-replaces', 'option-precedence', value({ defaultLayoutOptions: { 'elk.direction': 'DOWN' } }), graph(), [{ id: 'layout-1', method: 'layout', graphKey: 'g', arguments: value({ layoutOptions: { 'elk.direction': 'LEFT' } }) }]);
  const local = graph(); local.layoutOptions['elk.direction'] = 'RIGHT';
  add('precedence-root-local-wins', 'option-precedence', value({ defaultLayoutOptions: { 'elk.direction': 'DOWN' } }), local, [{ id: 'layout-1', method: 'layout', graphKey: 'g', arguments: value({ layoutOptions: { 'elk.direction': 'LEFT' } }) }]);
  add('logging-same-graph-reuse', 'same-instance-input-side-effects', omitted(), graph(), [
    { id: 'logging-on', method: 'layout', graphKey: 'g', arguments: value({ logging: true }) },
    { id: 'logging-default-next-call', method: 'layout', graphKey: 'g', arguments: omitted() }
  ]);
  for (const [name, hash] of [['zero', 0], ['false', false], ['null', null], ['string', 'user-hash'], ['positive-integer', 777]]) {
    for (const owner of ['root', 'child']) {
      const g = graph(); (owner === 'root' ? g : g.children[0]).$H = hash;
      add('user-hash-' + owner + '-' + name, 'user-owned-hash', omitted(), g);
    }
  }
  const nested = graph(); nested.business = { $H: 0, nested: { $H: 23, enabled: false }, error: { stack: 'user-owned stack must survive', name: 'BusinessData' } }; nested.children[0].data = { $H: false };
  add('user-hash-nested-business', 'user-owned-business-hash', omitted(), nested);
  const unknownEndpoint = graph(); unknownEndpoint.edges[0].targets = ['missing'];
  add('error-unknown-endpoint', 'error-side-effects', omitted(), unknownEndpoint);
  const unknownAlgorithm = graph(); unknownAlgorithm.layoutOptions['elk.algorithm'] = 'not-a-layout-algorithm';
  add('error-unknown-algorithm', 'error-side-effects', omitted(), unknownAlgorithm);
  add('lifecycle-terminate-before-layout', 'fake-worker-lifecycle', omitted(), graph(), [
    { id: 'terminate-1', method: 'terminateWorker' }, { id: 'layout-after-terminate', method: 'layout', graphKey: 'g', arguments: omitted() }
  ]);
  add('lifecycle-repeat-terminate', 'fake-worker-lifecycle', omitted(), graph(), [
    { id: 'layout-before', method: 'layout', graphKey: 'g', arguments: omitted() },
    { id: 'terminate-1', method: 'terminateWorker' }, { id: 'terminate-2', method: 'terminateWorker' },
    { id: 'layout-after-terminate', method: 'layout', graphKey: 'g', arguments: omitted() }
  ]);
  add('worker-url-empty', 'node-worker-parameter', value({ workerUrl: '' }));
  add('worker-url-missing-file', 'node-worker-parameter', value({ workerUrl: './does-not-exist.js' }));
  add('worker-factory-invalid-string', 'node-worker-parameter', value({ workerFactory: 'not-a-function' }));
  return probes;
}

function decode(form) {
  if (!form || !['value', 'undefined', 'omitted'].includes(form.kind)) throw new Error('Invalid value descriptor');
  return form.kind === 'value' ? clone(form.value) : undefined;
}

function verifyPackage(packageRoot, lock) {
  if (lock.javascript.version !== '0.12.1' || lock.javascript.commit !== '624ae90aa37110033a8af59c5ccbb292708b4317') throw new Error('Behavior baseline differs');
  for (const [name, sha] of Object.entries(lock.distribution.sha256Files)) {
    if (digest(fs.readFileSync(path.join(packageRoot, name))) !== sha) throw new Error('Locked package hash differs: ' + name);
  }
}

async function invoke(operation, timeoutMs) {
  let timer;
  let result;
  try { result = operation(); }
  catch (e) { return { outcome: 'threw', returnStyle: 'synchronous_throw', error: errorRecord(e) }; }
  const thenable = result !== null && result !== undefined && typeof result.then === 'function';
  try {
    const settled = thenable ? await Promise.race([result, new Promise((_, reject) => { timer = setTimeout(() => { const e = new Error('Probe operation timed out'); e.name = 'ContractProbeTimeout'; reject(e); }, timeoutMs); })]) : result;
    return { outcome: 'returned', returnStyle: thenable ? 'promise' : 'synchronous', result: snapshot(settled) };
  } catch (e) {
    return { outcome: e.name === 'ContractProbeTimeout' ? 'timed_out' : 'threw', returnStyle: thenable ? 'promise' : 'synchronous', error: errorRecord(e) };
  } finally { clearTimeout(timer); }
}

async function child(packageRoot, specPath, outputPath) {
  const lock = JSON.parse(fs.readFileSync(path.join(ROOT, 'UPSTREAM.json'), 'utf8'));
  verifyPackage(packageRoot, lock);
  const specBytes = fs.readFileSync(specPath);
  const spec = JSON.parse(specBytes);
  const ELK = require(path.join(packageRoot, 'lib/elk.bundled.js'));
  const ctor = decode(spec.constructor);
  if (ctor !== null && typeof ctor === 'object') for (const field of spec.constructorUndefinedFields || []) ctor[field] = undefined;
  const graphs = Object.fromEntries(Object.entries(spec.graphs).map(([key, form]) => [key, decode(form)]));
  const report = { schema: 'py-elk-contract-observation/v1', id: spec.id, requestSha256: digest(specBytes),
    engine: { name: 'elkjs', version: lock.javascript.version, node: process.version, platform: process.platform, arch: process.arch,
      entrypointSha256: lock.distribution.sha256Files['lib/elk.bundled.js'] },
    actualConstructor: { argumentKind: spec.constructor.kind, explicitlyUndefinedFields: spec.constructorUndefinedFields || [] }, calls: [] };
  let elk;
  const beforeCtor = snapshot(ctor);
  try { elk = spec.constructor.kind === 'omitted' ? new ELK() : new ELK(ctor); report.constructor = { outcome: 'returned', returnStyle: 'synchronous', before: beforeCtor, after: snapshot(ctor) }; }
  catch (e) { report.constructor = { outcome: 'threw', returnStyle: 'synchronous_throw', error: errorRecord(e), before: beforeCtor, after: snapshot(ctor) }; }
  if (elk) {
    for (const call of spec.calls) {
      const args = call.arguments ? decode(call.arguments) : undefined;
      if (args !== undefined && args !== null && typeof args === 'object') for (const field of call.undefinedFields || []) args[field] = undefined;
      const g = call.graphKey === null || call.graphKey === undefined ? undefined : graphs[call.graphKey];
      const before = { graph: snapshot(g), constructor: snapshot(ctor), arguments: snapshot(args) };
      const actual = { graphArgumentKind: call.graphKey === null ? 'omitted' : spec.graphs[call.graphKey]?.kind || 'not_applicable',
        argumentKind: call.arguments?.kind || 'not_applicable', explicitlyUndefinedFields: call.undefinedFields || [] };
      const observed = await invoke(() => {
        if (call.method === 'terminateWorker') return elk.terminateWorker();
        if (call.method !== 'layout') throw new Error('Unknown probe operation');
        if (call.graphKey === null) return elk.layout();
        return call.arguments.kind === 'omitted' ? elk.layout(g) : elk.layout(g, args);
      }, 1200);
      report.calls.push({ id: call.id, method: call.method, actualArguments: actual, before, ...observed,
        after: { graph: snapshot(g), constructor: snapshot(ctor), arguments: snapshot(args) } });
      if (observed.outcome === 'timed_out') { process.exitCode = 3; break; }
    }
    report.finalTermination = await invoke(() => elk.terminateWorker(), 1200);
    if (report.finalTermination.outcome === 'timed_out') process.exitCode = 3;
  } else { report.skippedOperations = spec.calls.map(c => c.id); }
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
}

function removeNewShapeHashes(original, after) {
  if (!original || !after || typeof original !== 'object' || typeof after !== 'object') return after;
  const copy = clone(after);
  const walk = (a, b) => {
    if (!Object.prototype.hasOwnProperty.call(a, '$H')) delete b.$H;
    if (Array.isArray(a.children) && Array.isArray(b.children) && a.children.length === b.children.length) for (let i = 0; i < a.children.length; i++) walk(a.children[i], b.children[i]);
  };
  walk(original, copy);
  return copy;
}

function summaryFlags(spec, observed) {
  return observed.calls.map(call => {
    const before = call.before.graph, after = call.after.graph;
    return { callId: call.id, outcome: call.outcome, returnStyle: call.returnStyle,
      resultExactlyInputAfter: call.outcome === 'returned' && JSON.stringify(call.result) === JSON.stringify(after),
      graphUnchanged: JSON.stringify(before) === JSON.stringify(after),
      graphOnlyNewShapeHashAdditions: before.kind === 'value' && after.kind === 'value' && JSON.stringify(before.value) === JSON.stringify(removeNewShapeHashes(before.value, after.value)),
      constructorUnchanged: JSON.stringify(call.before.constructor) === JSON.stringify(call.after.constructor),
      argumentsUnchanged: JSON.stringify(call.before.arguments) === JSON.stringify(call.after.arguments) };
  });
}

function withoutStacks(observation) {
  const copy = clone(observation);
  // Only tool-owned error records lose platform-specific stacks in the summary.
  // A user graph may itself contain business.error.stack, which remains exact.
  for (const record of [copy.constructor, ...copy.calls, copy.finalTermination]) if (record?.error) delete record.error.stack;
  return copy;
}

async function main() {
  if (process.argv[2] === '--child') return child(path.resolve(process.argv[3]), process.argv[4], process.argv[5]);
  const [packagePath, outputPath, ...extra] = process.argv.slice(2);
  if (!packagePath || !outputPath) throw new Error('Usage: node capture_contracts.cjs PACKAGE NEW_OUTPUT [--summary NEW_JSON] [--only PROBE_ID] [--timeout-ms INTEGER]');
  let summaryPath = null, timeoutMs = 5000;
  const only = [];
  for (let i = 0; i < extra.length; i += 2) {
    if (extra[i] === '--summary') summaryPath = path.resolve(extra[i + 1]);
    else if (extra[i] === '--only') only.push(extra[i + 1]);
    else if (extra[i] === '--timeout-ms') timeoutMs = Number(extra[i + 1]);
    else throw new Error('Unknown argument: ' + extra[i]);
  }
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 30000) throw new Error('Invalid timeout');
  const packageRoot = path.resolve(packagePath), out = path.resolve(outputPath);
  const lock = JSON.parse(fs.readFileSync(path.join(ROOT, 'UPSTREAM.json'), 'utf8'));
  verifyPackage(packageRoot, lock);
  if (fs.existsSync(out) || (summaryPath && fs.existsSync(summaryPath))) throw new Error('Output already exists');
  const probes = catalogue().filter(p => !only.length || only.includes(p.id));
  if (!probes.length || only.some(id => !probes.some(p => p.id === id))) throw new Error('Unknown or empty probe selection');
  fs.mkdirSync(out, { recursive: true });
  const result = { schema: 'py-elk-contract-probes/v1', status: 'CAPTURED',
    baseline: { version: lock.javascript.version, commit: lock.javascript.commit, entrypointSha256: lock.distribution.sha256Files['lib/elk.bundled.js'] },
    tool: { path: 'tools/reference/capture_contracts.cjs', sha256: digest(fs.readFileSync(__filename)) },
    sources: [
      { sourceId: 'elkjs-api', path: 'src/js/elk-api.js', commit: lock.javascript.commit, sha256: lock.sourceSha256['src/js/elk-api.js'] },
      { sourceId: 'elkjs-node-entry', path: 'src/js/main-node.js', commit: lock.javascript.commit, sha256: lock.sourceSha256['src/js/main-node.js'] },
      { sourceId: 'elkjs-bundled', path: 'lib/elk.bundled.js', commit: lock.javascript.commit, sha256: lock.distribution.sha256Files['lib/elk.bundled.js'] }
    ], environment: { node: process.version, platform: process.platform, arch: process.arch }, probes: [],
    pythonAlgorithmsVerified: 0, limitation: 'Official bundled/FakeWorker probes only; throws remain throws, timeouts/process failures are incomplete, no native Python or lifecycle parity accepted.' };
  for (const spec of probes) {
    const directory = path.join(out, spec.id); fs.mkdirSync(directory);
    const requestPath = path.join(directory, 'request.json'), observationPath = path.join(directory, 'observation.json');
    fs.writeFileSync(requestPath, JSON.stringify(spec, null, 2) + '\n', { flag: 'wx' });
    const argv = [__filename, '--child', packageRoot, requestPath, observationPath];
    const started = Date.now();
    const childResult = cp.spawnSync(process.execPath, argv, { timeout: timeoutMs, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
    fs.writeFileSync(path.join(directory, 'stdout.log'), childResult.stdout || '', { flag: 'wx' });
    fs.writeFileSync(path.join(directory, 'stderr.log'), childResult.stderr || '', { flag: 'wx' });
    const command = { argv: [process.execPath, ...argv], cwd: process.cwd(), exitCode: childResult.status, signal: childResult.signal,
      spawnError: childResult.error ? String(childResult.error) : null, elapsedMs: Date.now() - started };
    fs.writeFileSync(path.join(directory, 'command.json'), JSON.stringify(command, null, 2) + '\n', { flag: 'wx' });
    let observation = null;
    if (fs.existsSync(observationPath)) observation = JSON.parse(fs.readFileSync(observationPath, 'utf8'));
    const timedOutObservation = observation && [observation.constructor, ...observation.calls, observation.finalTermination]
      .some(operation => operation && operation.outcome === 'timed_out');
    if (childResult.status !== 0 || !observation || timedOutObservation) result.status = 'INCOMPLETE';
    result.probes.push({ id: spec.id, category: spec.category, input: spec, observation: observation ? withoutStacks(observation) : null,
      flags: observation ? summaryFlags(spec, observation) : [], process: command,
      rawObservationPath: observation ? path.relative(ROOT, observationPath).replaceAll('\\', '/') : null,
      rawObservationSha256: observation ? digest(fs.readFileSync(observationPath)) : null,
      requestBytesBase64: fs.readFileSync(requestPath).toString('base64'),
      requestSha256: digest(fs.readFileSync(requestPath)) });
  }
  result.probeCount = result.probes.length;
  fs.writeFileSync(path.join(out, 'index.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  if (summaryPath) { fs.mkdirSync(path.dirname(summaryPath), { recursive: true }); fs.writeFileSync(summaryPath, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' }); }
  console.log(JSON.stringify({ status: result.status, probeCount: result.probeCount, index: path.join(out, 'index.json') }, null, 2));
  if (result.status !== 'CAPTURED') process.exitCode = 2;
}
main().catch(e => { console.error(e.stack || e); process.exitCode = 2; });
