// Dependency-free state-machine checks. Plotly and Pyodide are stubbed;
// this is not visual/browser QA. Run: node tests/test_app.cjs
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert/strict');

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const elements = new Map();

class Element {
  constructor(id = '') {
    this.id = id;
    this.children = [];
    this.dataset = {};
    this.style = {};
    this.value = '';
    this.max = '';
    this.disabled = false;
    this.checked = true;
    this.textContent = '';
    this.handlers = {};
    this.classes = new Set();
    this.classList = {
      toggle: (name, on) => on ? this.classes.add(name) : this.classes.delete(name),
      add: name => this.classes.add(name),
      remove: name => this.classes.delete(name),
    };
  }

  set innerHTML(value) {
    this.html = value;
    this.children = [];
  }

  get innerHTML() {
    return this.html || '';
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  append(...children) {
    this.children.push(...children);
  }

  setAttribute(name, value) {
    this[name] = value;
  }

  addEventListener(name, handler) {
    this.handlers[name] = handler;
  }

  querySelector(selector) {
    this.parts ??= {};
    return this.parts[selector] ??= new Element();
  }

  click() {}
  remove() {}

  on(name, handler) {
    this.handlers[name] = handler;
  }

  removeAllListeners(name) {
    delete this.handlers[name];
  }
}

function element(id) {
  if (!elements.has(id)) elements.set(id, new Element(id));
  return elements.get(id);
}

const document = {
  getElementById: element,
  createElement: () => new Element(),
  body: new Element('body'),
  querySelectorAll(selector) {
    if (selector === '#roles select') {
      return element('roles').children.flatMap(row => row.children)
        .filter(child => child.dataset.role);
    }
    if (selector === '.coll') {
      return element('colls').children.filter(child => child.dataset.name);
    }
    return [];
  },
};

const routes = new Map([
  ['collection_domains.json', { domains: {} }],
  ['events/index.json', { events: [] }],
  ['wheels/index.json', { wheel: 'test.whl' }],
]);
let activePlots = 0;
let maxPlots = 0;
let plotWait = 0;
let activePython = 0;
let maxPython = 0;
let pythonWait = 0;
const globals = new Map();
const pythonCalls = [];

const figure = view => ({
  data: [{ opacity: 0.2, meta: { collection: 'A' } }, { meta: { collection: 'B' } }],
  layout: {
    meta: { view, run: 1, event: 2, source: 'input.root' },
    width: view === 'panels' ? 1500 : 1250,
    height: view === 'panels' ? 1450 : 900,
  },
});
const schema = {
  roles: { tracks: 'A' },
  collections: {
    A: { kind: 'Track', count: 1, type: 'Track', links: [] },
    B: { kind: 'Cluster', count: 1, type: 'Cluster', links: [] },
  },
};
const resultViews = () => ({
  figure: figure('panels'),
  figure3d: figure('3d'),
  figureflow2d: figure('flow2d'),
  figureflow3d: figure('flow3d'),
  schema,
});
const python = {
  globals: { set: (name, value) => globals.set(name, value) },
  FS: { mkdir() {}, writeFile() {} },
  async loadPackage() {},
  pyimport() {
    return { async install() {} };
  },
  async runPythonAsync(code) {
    pythonCalls.push(code);
    maxPython = Math.max(maxPython, ++activePython);
    await delay(pythonWait);
    --activePython;
    if (code.includes('n_entries(')) return 2;
    return JSON.stringify(resultViews());
  },
};
const context = {
  document, console, URL, URLSearchParams, Blob, setTimeout, clearTimeout, Uint8Array,
  location: { href: 'https://example.org/app.html', search: '' },
  loadPyodide: async () => python,
  async fetch(url) {
    const route = routes.get(url);
    if (route?.wait) await delay(route.wait);
    return { ok: !!route, status: route ? 200 : 404, json: async () => route?.body ?? route };
  },
  Plotly: {
    async newPlot(canvas, data, layout) {
      maxPlots = Math.max(maxPlots, ++activePlots);
      await delay(plotWait);
      canvas.data = data;
      canvas.layout = layout;
      --activePlots;
    },
    async restyle(canvas, change) {
      canvas.data.forEach((trace, index) => trace.opacity = change.opacity[index]);
    },
    purge(canvas) {
      assert.equal(activePlots, 0, 'purge must wait for an in-flight newPlot');
      delete canvas.data;
      delete canvas.layout;
    },
    downloadImage() {},
  },
};
vm.createContext(context);
let code = fs.readFileSync(path.join(__dirname, '../docs/app.html'), 'utf8')
  .split('<script>')[1].split('</script>')[0];
const expose = `globalThis.app = {
  show, pickView, loadShowcase, loadFile, render, select, saveName,
  setManifest: value => manifest = value,
  get state() {
    return { dimension, frame, figs, figure, schema, request, busy, plotting, mode, loadedName };
  }
};`;
code = code.replace(/\}\)\(\);\s*$/, expose + '})();');
vm.runInContext(code, context);
const app = context.app;
const file = name => ({ name, size: 1, arrayBuffer: async () => new ArrayBuffer(1) });

async function checkInterruptedDraw({ queued = false, fail = false, showcase = false } = {}) {
  plotWait = 0;
  await app.show({ '2d:lab': figure('panels'), '3d:lab': figure('3d') }, schema);
  await app.pickView('dimension', '2d');
  plotWait = 30;
  const switching = app.pickView('dimension', '3d');
  if (!queued) await delay(3);
  let loading;
  if (showcase) {
    app.setManifest({ events: [{ key: 'missing', file: 'missing.json', title: 'missing' }] });
    loading = app.loadShowcase('missing');
  } else {
    const nextFile = file('next.root');
    if (fail) nextFile.arrayBuffer = async () => { throw new Error('file read failed'); };
    loading = app.loadFile(nextFile);
  }
  await Promise.all([switching, loading]);
  await delay(0); // drain the queued purge
  assert.equal(app.state.figure, null, 'an interrupted drawing cannot remain exportable');
  assert.equal(element('canvas').style.display, 'none');
  assert.equal(element('canvas').layout, undefined, 'obsolete Plotly state was purged');
  for (const id of ['savePng', 'saveSvg', 'saveJson']) assert.equal(element(id).disabled, true);
  assert.equal(app.state.plotting, false);
  assert.equal(app.state.busy, false);
  plotWait = 0;
  if (!fail && !showcase) {
    await app.render();
    assert.equal(app.state.figure.layout.meta.view, element('canvas').layout.meta.view);
    assert.equal(app.state.figure.layout.width, element('canvas').layout.width);
    assert.equal(element('savePng').disabled, false);
  }
}

(async () => {
  await delay(10);
  const views = {
    '2d:lab': figure('panels'),
    '3d:lab': figure('3d'),
    '2d:poynt': figure('flow2d'),
    '3d:poynt': figure('flow3d'),
  };
  await app.show(views, schema);
  assert.equal(app.state.dimension, '2d');
  assert.equal(app.state.frame, 'lab');
  await app.pickView('frame', 'poynt');
  assert.equal(element('canvas').layout.meta.view, 'flow2d');
  assert.equal(app.saveName(), 'delphi_run1_evt2_poynt');
  await app.pickView('dimension', '3d');
  assert.equal(element('canvas').layout.meta.view, 'flow3d');
  assert.equal(app.saveName(), 'delphi_run1_evt2_3d_poynt');

  await app.select('B');
  assert.equal(element('canvas').data[0].opacity, 0.024);
  assert.equal(views['3d:poynt'].data[0].opacity, 0.2);
  await app.pickView('frame', 'lab');
  assert.equal(element('canvas').data[0].opacity, 0.024);
  await app.select(null);
  assert.equal(element('canvas').data[0].opacity, 0.2);

  plotWait = 25;
  const first = app.pickView('frame', 'poynt');
  await delay(2);
  const second = app.pickView('dimension', '2d');
  await Promise.all([first, second]);
  assert.equal(element('canvas').layout.meta.view, 'flow2d');
  assert.equal(maxPlots, 1);
  assert.equal(app.state.plotting, false);
  plotWait = 0;

  await app.show({ '2d:lab': figure('panels'), '3d:poynt': figure('flow3d') }, schema);
  await app.pickView('dimension', '3d');
  assert.equal(app.state.frame, 'poynt');
  await app.pickView('frame', 'lab');
  assert.equal(app.state.dimension, '2d');

  app.setManifest({ events: [
    { key: 'slow', file: 'slow.json', title: 'slow' },
    { key: 'fast', file: 'fast.json', title: 'fast' },
  ] });
  routes.set('slow.json', { wait: 40, body: figure('flow3d') });
  routes.set('fast.json', figure('panels'));
  await Promise.all([app.loadShowcase('slow'), app.loadShowcase('fast')]);
  assert.equal(element('canvas').layout.meta.view, 'panels');
  assert.equal(app.state.busy, false);
  assert.equal(element('fpoynt').disabled, true);
  assert(element('status').textContent.includes('--view all'));
  await app.loadShowcase('slow');
  assert.equal(app.state.dimension, '3d');
  assert.equal(app.state.frame, 'poynt');
  assert.equal(element('canvas').layout.meta.view, 'flow3d');
  assert.equal(element('roles').textContent, 'no collection metadata available');

  pythonWait = 25;
  element('entry').value = '0';
  await app.loadFile(file('weird"name.root'));
  assert.equal(app.state.mode, 'live');
  assert.equal(element('entry').max, 1);
  await app.render();
  assert.equal(maxPython, 1);
  assert(pythonCalls.some(call => call.includes('build_flow2d')));
  assert(!pythonCalls.some(call => call.includes('weird')));
  assert.equal(globals.get('SOURCE_NAME'), 'weird"name.root');
  const calls = pythonCalls.length;
  element('entry').value = '2';
  await app.render();
  assert.equal(pythonCalls.length, calls);
  assert(element('status').textContent.includes('choose an entry'));

  element('entry').value = '0';
  const rendering = app.render();
  await delay(2);
  const loading = app.loadFile(file('new.root'));
  await Promise.all([rendering, loading]);
  assert.equal(maxPython, 1);
  assert.equal(app.state.loadedName, 'new.root');
  assert.equal(app.state.schema, null);
  assert.equal(app.state.busy, false);
  assert.equal(app.state.plotting, false);

  // Regression: a new file/event interrupts either a queued or an active Plotly call.
  // Success and failure must both leave exports disabled until a fresh figure is drawn.
  pythonWait = 0;
  await checkInterruptedDraw();
  await checkInterruptedDraw({ queued: true });
  await checkInterruptedDraw({ fail: true });
  await checkInterruptedDraw({ showcase: true });
  await checkInterruptedDraw({ showcase: true, queued: true });
  console.log('PASS: four views/exports, opacity, rapid switches, fallbacks, stale fetches, '
    + 'primary classification, live reload/bounds, safe Python values, and interrupted Plotly regressions.');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
