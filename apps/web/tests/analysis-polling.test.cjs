const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function setup(statuses) {
  const timers = new Map();
  let id = 0;
  let calls = 0;
  const document = { hidden: false };
  const exports = {};
  const context = {
    exports, document, AbortController,
    setTimeout: (fn, delay) => { timers.set(++id, { fn, delay }); return id; },
    clearTimeout: key => timers.delete(key),
    fetch: async () => {
      const status = statuses[Math.min(calls++, statuses.length - 1)];
      if (status === 'error') throw new Error('offline');
      return { ok: true, json: async () => ({ job: { status } }) };
    },
  };
  const source = fs.readFileSync(path.join(__dirname, '../lib/analysis-polling.ts'), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  return {
    timers, document, start: exports.pollAnalysis, calls: () => calls,
    async tick() {
      const [key, timer] = [...timers][0];
      timers.delete(key);
      await timer.fn();
    },
  };
}

test('backs off unchanged jobs and stops on completion', async () => {
  const s = setup(['running', 'running', 'completed']);
  const received = [];
  s.start('B30006', x => received.push(x));
  await s.tick();
  assert.equal([...s.timers.values()][0].delay, 3000);
  await s.tick();
  assert.equal([...s.timers.values()][0].delay, 4500);
  await s.tick();
  assert.equal(s.timers.size, 0);
  assert.equal(received.length, 3);
});

test('hidden tabs pause requests and cleanup removes timers', async () => {
  const s = setup(['running']);
  s.document.hidden = true;
  const stop = s.start('B30006', () => {});
  await s.tick();
  assert.equal(s.calls(), 0);
  assert.equal([...s.timers.values()][0].delay, 15000);
  stop();
  assert.equal(s.timers.size, 0);
});

test('network errors back off without unhandled rejection', async () => {
  const s = setup(['error']);
  const stop = s.start('B30006', () => assert.fail('unexpected update'));
  await s.tick();
  assert.equal([...s.timers.values()][0].delay, 6000);
  stop();
});
