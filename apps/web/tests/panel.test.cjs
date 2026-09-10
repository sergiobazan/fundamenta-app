const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const output = { exports: {} };
const source = fs.readFileSync(path.join(__dirname, '../lib/panel.ts'), 'utf8');
vm.runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, output);
const { panelOverview } = output.exports;
const company = (id, fields = {}) => ({ smv_rpj: id, legal_name: id,
  has_analysis: false, analysis_status: 'not_analyzed', support_level: 'basic', ...fields });

test('empty catalog shows zero actual counts', () => {
  const result = panelOverview([]);
  assert.equal(result.compatible, 0);
  assert.equal(result.available.length, 0);
  assert.equal(result.active.length, 0);
  assert.equal(result.attention, 0);
});

test('counts available, incompatible, partial and processing separately', () => {
  const rows = [company('industry', { has_analysis: true, analysis_status: 'available' }),
    company('bank', { support_level: 'unsupported', analysis_status: 'unsupported' }),
    company('partial', { has_analysis: true, analysis_status: 'partial' }),
    company('retry', { has_analysis: true, analysis_status: 'partial', job_status: 'retrying' })];
  const result = panelOverview(rows);
  assert.equal(result.compatible, 3);
  assert.equal(result.available.length, 1);
  assert.equal(result.available[0].smv_rpj, 'industry');
  assert.equal(result.active.length, 1);
  assert.equal(result.attention, 1);
});

test('available companies sorted by completion, no hardcoded mining selection', () => {
  const rows = [company('mining', { has_analysis: true, analysis_status: 'available', last_completed_at: '2025-01-01' }),
    company('food', { has_analysis: true, analysis_status: 'available', last_completed_at: '2026-01-01' })];
  assert.equal(panelOverview(rows).available[0].smv_rpj, 'food');
  assert.equal(rows[0].smv_rpj, 'mining');
});
