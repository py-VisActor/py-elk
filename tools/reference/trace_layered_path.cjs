// Development-only E01 path audit. Never used by Python layout runtime.
// Original npm files remain untouched; PRETTY worker hooks exist in memory only.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Module = require('node:module');
const childProcess = require('node:child_process');
const util = require('node:util');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
const root = path.resolve(__dirname, '../..');
const lock = JSON.parse(fs.readFileSync(path.join(root, 'UPSTREAM.json'), 'utf8'));

function verify(packageRoot) {
  for (const [name, digest] of Object.entries(lock.distribution.sha256Files)) {
    if (sha(fs.readFileSync(path.join(packageRoot, name))) !== digest) throw new Error('Locked npm SHA differs: ' + name);
  }
}
function write(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n', { flag: 'wx' });
}
function validateDomain(request) {
  const graph = request.graph;
  if (!graph || typeof graph !== 'object' || Array.isArray(graph)) throw new Error('Trace domain requires a root graph object');
  const children = graph.children || [];
  const edges = graph.edges || [];
  if (!Array.isArray(children) || !Array.isArray(edges)) throw new Error('Trace domain requires child/edge arrays');
  for (const shape of [graph, ...children]) {
    if (!shape || typeof shape !== 'object' || (shape.ports && shape.ports.length) || (shape.labels && shape.labels.length)) throw new Error('Trace domain excludes explicit ports and labels');
    if (shape !== graph && ((shape.children && shape.children.length) || (shape.edges && shape.edges.length))) throw new Error('Trace domain excludes nested graphs');
  }
  if (edges.some(edge => !Array.isArray(edge.sources) || edge.sources.length !== 1 || !Array.isArray(edge.targets) || edge.targets.length !== 1 || (edge.labels && edge.labels.length))) throw new Error('Trace domain requires single-source/target extended edges without labels');
  const optionSets = [graph.layoutOptions || {}, request.layoutArguments.layoutOptions || {}, request.constructor.defaultLayoutOptions || {}];
  for (const options of optionSets) {
    for (const [key, value] of Object.entries(options)) {
      if (key.endsWith('hierarchyHandling') && value === 'INCLUDE_CHILDREN') throw new Error('Trace domain excludes hierarchy-aware execution');
    }
  }
}
function hooks(source) {
  const transformations = [];
  let result = source;
  function replace(id, match, replacement) {
    if (result.split(match).length !== 2) throw new Error('Hook anchor must occur exactly once: ' + id);
    const line = source.slice(0, source.indexOf(match)).split('\n').length;
    result = result.replace(match, replacement);
    transformations.push({ id, originalLine: line, match, replacement });
  }
  replace('component-entry', 'function $layout_1(lgraph, monitor){',
    'function $layout_1(lgraph, monitor){\n  global.__pyelkE01Trace.push({event:"component-entry",layerlessNodes:lgraph.layerlessNodes.array.length});');
  replace('processor-call', '    processor.process(lgraph, monitor.subTask(monitorProgress));',
    '    global.__pyelkE01Trace.push({event:"processor-before",name:$getName(getClass__Ljava_lang_Class___devirtual$(processor)),layerCount:lgraph.layers.array.length});\n' +
    '    processor.process(lgraph, monitor.subTask(monitorProgress));\n' +
    '    global.__pyelkE01Trace.push({event:"processor-after",name:$getName(getClass__Ljava_lang_Class___devirtual$(processor)),layerCount:lgraph.layers.array.length});');
  replace('configured-options', '  $setProperty_0(lgraph, PROCESSORS, $build_0(this$static.algorithmAssembler, lgraph));',
    '  $setProperty_0(lgraph, PROCESSORS, $build_0(this$static.algorithmAssembler, lgraph));\n' +
    '  global.__pyelkE01Trace.push({event:"configured-options",direction:$getProperty(lgraph,DIRECTION).name_0,edgeRouting:$getProperty(lgraph,EDGE_ROUTING).name_0,randomSeed:$getProperty(lgraph,RANDOM_SEED_0).value_0,' +
    'padding:{top:lgraph.padding.top_0,left:lgraph.padding.left,bottom:lgraph.padding.bottom,right:lgraph.padding.right},' +
    'nodeNode:$doubleValue(castToDouble($getProperty(lgraph,SPACING_NODE_NODE_0))),betweenLayers:$doubleValue(castToDouble($getProperty(lgraph,SPACING_NODE_NODE_BETWEEN_LAYERS_0))),' +
    'componentComponent:$doubleValue(castToDouble($getProperty(lgraph,SPACING_COMPONENT_COMPONENT_0))),separateConnectedComponents:$booleanValue(castToBoolean($getProperty(lgraph,SEPARATE_CONNECTED_COMPONENTS_0))),' +
    'cycleBreaking:$getProperty(lgraph,CYCLE_BREAKING_STRATEGY_0).name_0,layering:$getProperty(lgraph,LAYERING_STRATEGY_0).name_0,crossingMinimization:$getProperty(lgraph,CROSSING_MINIMIZATION_STRATEGY_0).name_0,nodePlacement:$getProperty(lgraph,NODE_PLACEMENT_STRATEGY_0).name_0});');
  return { source: result, transformations };
}
async function child(kind, packageRoot, requestFile, outputFile) {
  verify(packageRoot);
  const requestBytes = fs.readFileSync(requestFile);
  const request = JSON.parse(requestBytes.toString('utf8'));
  if (request.schema !== 'py-elk-layout-request/v1') throw new Error('Invalid request');
  validateDomain(request);
  const graph = clone(request.graph);
  const constructor = clone(request.constructor);
  const arguments_ = { ...clone(request.layoutArguments), logging: true, measureExecutionTime: false };
  const events = [];
  let transformations = [];
  let elk;
  if (kind === 'bundled') {
    const ELK = require(path.join(packageRoot, 'lib/elk.bundled.js'));
    elk = new ELK(constructor);
  } else {
    const workerFile = path.join(packageRoot, 'lib/elk-worker.js');
    let Worker;
    if (kind === 'instrumented-pretty') {
      const original = fs.readFileSync(workerFile, 'utf8');
      const instrumented = hooks(original);
      transformations = instrumented.transformations;
      global.__pyelkE01Trace = events;
      const generated = new Module(workerFile, module);
      generated.filename = workerFile;
      generated.paths = Module._nodeModulePaths(path.dirname(workerFile));
      generated._compile(instrumented.source, workerFile);
      Worker = generated.exports.Worker;
    } else {
      Worker = require(workerFile).Worker;
    }
    const ELK = require(path.join(packageRoot, 'lib/elk-api.js')).default;
    elk = new ELK({ ...constructor, workerFactory: () => new Worker() });
  }
  const observation = { schema: 'py-elk-layout-path-observation/v1', kind,
    requestSha256: sha(requestBytes), effectiveArguments: arguments_,
    node: process.version, platform: process.platform, workerSha256: lock.distribution.sha256Files['lib/elk-worker.js'],
    bundledSha256: lock.distribution.sha256Files['lib/elk.bundled.js'], memoryOnlyInstrumentation: kind === 'instrumented-pretty',
    transformations, events };
  try {
    observation.result = await elk.layout(graph, arguments_);
    observation.outcome = 'returned';
  } catch (error) {
    observation.outcome = 'threw';
    observation.error = { name: String(error.name || 'Error'), message: String(error.message || error), stack: String(error.stack || error) };
  }
  observation.inputAfter = graph;
  try {
    elk.terminateWorker();
    observation.termination = { outcome: 'returned' };
  } catch (error) {
    observation.termination = { outcome: 'threw', name: error.name, message: error.message };
  }
  write(outputFile, observation);
}
function summarizeLogging(result) {
  const configured = [];
  const monitorTasks = [];
  function visit(node, at) {
    if (!node || typeof node !== 'object') return;
    if (node.name) monitorTasks.push({ path: at, name: node.name });
    for (const value of node.logs || []) {
      const match = /^\s*Slot (\d+): (.+)$/.exec(value);
      if (match) configured.push({ path: at, slot: Number(match[1]), name: match[2] });
    }
    for (let i = 0; i < (node.children || []).length; i++) visit(node.children[i], at + '/children/' + i);
  }
  visit(result && result.logging, '/logging');
  return { configuredModules: configured, monitorTasks };
}
async function main() {
  const args = process.argv.slice(2);
  if (args[0] === '--child') return child(args[1], path.resolve(args[2]), path.resolve(args[3]), path.resolve(args[4]));
  const [packageArg, requestArg, outputArg] = args;
  if (!packageArg || !requestArg || !outputArg) throw new Error('Usage: node trace_layered_path.cjs PACKAGE REQUEST NEW_OUTPUT_DIRECTORY');
  const packageRoot = path.resolve(packageArg), requestFile = path.resolve(requestArg), output = path.resolve(outputArg);
  verify(packageRoot);
  validateDomain(JSON.parse(fs.readFileSync(requestFile, 'utf8')));
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.mkdirSync(output);
  fs.copyFileSync(requestFile, path.join(output, 'request.json'));
  const observations = {};
  const commands = [];
  for (const kind of ['bundled', 'pretty', 'instrumented-pretty']) {
    const observationFile = path.join(output, kind + '.json');
    const argv = [__filename, '--child', kind, packageRoot, requestFile, observationFile];
    const execution = childProcess.spawnSync(process.execPath, argv, { timeout: 30000, encoding: 'utf8' });
    fs.writeFileSync(path.join(output, kind + '-stdout.log'), execution.stdout || '', { flag: 'wx' });
    fs.writeFileSync(path.join(output, kind + '-stderr.log'), execution.stderr || String(execution.error || ''), { flag: 'wx' });
    commands.push({ argv: [process.execPath, ...argv], cwd: process.cwd(), exitCode: execution.status,
      error: execution.error ? String(execution.error) : null });
    if (execution.status !== 0) {
      write(path.join(output, 'commands.json'), commands);
      throw new Error(kind + ' failed; inspect saved stderr');
    }
    observations[kind] = JSON.parse(fs.readFileSync(observationFile, 'utf8'));
  }
  write(path.join(output, 'commands.json'), commands);
  const baseline = observations.bundled;
  const pretty = observations.pretty;
  const instrumented = observations['instrumented-pretty'];
  const report = { schema: 'py-elk-layered-path-trace/v1',
    status: 'PATH_TRACE_CAPTURED', requestSha256: sha(fs.readFileSync(requestFile)),
    traceDomain: 'Flat root/children, no explicit ports/labels; single-source/target extended edges; component processor loop only',
    requestSha256Meaning: 'SHA of original request bytes; actual layout arguments are separately recorded',
    argumentOverrides: { logging: true, measureExecutionTime: false },
    effectiveArguments: instrumented.effectiveArguments,
    workerSha256: lock.distribution.sha256Files['lib/elk-worker.js'],
    bundledSha256: lock.distribution.sha256Files['lib/elk.bundled.js'],
    prettyVersusBundledResultExact: util.isDeepStrictEqual(pretty.result, baseline.result),
    instrumentedVersusPrettyResultExact: util.isDeepStrictEqual(instrumented.result, pretty.result),
    observedCalls: instrumented.events.filter(e => e.event === 'processor-before'),
    completedCalls: instrumented.events.filter(e => e.event === 'processor-after'),
    configured: instrumented.events.filter(e => e.event === 'configured-options'),
    ...summarizeLogging(baseline.result),
    limitation: 'Development PRETTY-worker instrumentation, cross-checked against bundled output. Not Java source identity or Python implementation acceptance.' };
  report.outcomes = Object.fromEntries(Object.entries(observations).map(([kind, value]) => [kind, value.outcome]));
  report.callNamesMatchPublicLogging = util.isDeepStrictEqual(report.observedCalls.map(c => c.name), report.configuredModules.map(c => c.name));
  report.beforeAfterNamesMatch = util.isDeepStrictEqual(report.observedCalls.map(c => c.name), report.completedCalls.map(c => c.name));
  report.passed = Object.values(report.outcomes).every(outcome => outcome === 'returned') &&
    report.prettyVersusBundledResultExact && report.instrumentedVersusPrettyResultExact &&
    report.callNamesMatchPublicLogging && report.beforeAfterNamesMatch;
  if ((JSON.parse(fs.readFileSync(requestFile, 'utf8')).graph.children || []).length && !report.observedCalls.length) report.passed = false;
  report.files = Object.fromEntries(fs.readdirSync(output).map(name => [name, sha(fs.readFileSync(path.join(output, name)))]));
  write(path.join(output, 'report.json'), report);
  process.stdout.write(JSON.stringify({ status: report.status, observedCalls: report.observedCalls.length,
    passed: report.passed,
    prettyVersusBundledResultExact: report.prettyVersusBundledResultExact,
    instrumentedVersusPrettyResultExact: report.instrumentedVersusPrettyResultExact }) + '\n');
  if (!report.passed) process.exitCode = 1;
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 2; });
