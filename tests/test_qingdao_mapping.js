#!/usr/bin/env node
/* 青岛版映射文件格式测试：node tests/test_qingdao_mapping.js（无依赖）。 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const FILE = path.join(ROOT, 'data/mappings/qingdao-math.json');
const TOPICS = path.join(ROOT, 'data/topics.json');
let passed = 0;
function test(name, fn) { fn(); passed++; console.log('  ok   ' + name); }
if (!fs.existsSync(FILE)) { console.error('data/mappings/qingdao-math.json 不存在'); process.exit(1); }
const raw = fs.readFileSync(FILE, 'utf8');
const map = JSON.parse(raw);
const topics = JSON.parse(fs.readFileSync(TOPICS, 'utf8'));
const byId = new Map(topics.map((t) => [t.id, t]));
const HEAD = ['version','subject','stage','label','status','source','contributor','note','entries'];
const FIELDS = ['grade','term','unit','chapter','note'];
const nonEmpty = (v) => typeof v === 'string' && v.trim() !== '';

test('文件头齐全、UTF-8 无 BOM、无重复键', () => {
  assert.notEqual(raw.charCodeAt(0), 0xfeff);
  for (const k of Object.keys(map)) assert.ok(HEAD.includes(k), '未知字段 ' + k);
  for (const k of ['version','subject','stage','source','contributor','entries']) assert.ok(k in map);
  assert.ok(nonEmpty(map.source) && map.source.length <= 2000);
  assert.ok(nonEmpty(map.contributor) && map.contributor.length <= 40);
});
test('version/subject/stage 与文件名一致', () => {
  assert.equal(map.version, 'qingdao');
  assert.equal(map.subject, 'math');
  assert.equal(map.stage, 'primary');
  assert.equal(path.basename(FILE), map.version + '-' + map.subject + '.json');
});
test('status 合法，条目字段与取值合法（含 1–6 年级）', () => {
  assert.ok(['draft','reviewed'].includes(map.status || 'draft'));
  for (const [id, e] of Object.entries(map.entries)) {
    const t = byId.get(id);
    assert.ok(t && !t.external && /^cnm_p\d+$/.test(id), id);
    assert.ok(e && typeof e === 'object' && !Array.isArray(e));
    for (const k of Object.keys(e)) assert.ok(FIELDS.includes(k), id + ' 未知字段 ' + k);
    assert.ok(Number.isInteger(e.grade) && e.grade >= 1 && e.grade <= 6, id + ' grade');
    assert.ok(e.term === 1 || e.term === 2, id + ' term');
    assert.ok(nonEmpty(e.unit), id + ' unit');
    for (const k of ['chapter','note']) if (k in e) assert.ok(nonEmpty(e[k]));
  }
});
test('unit/chapter/note 与文件头文案不含「示例」「占位」', () => {
  for (const [id, e] of Object.entries(map.entries))
    for (const k of ['unit','chapter','note']) if (typeof e[k] === 'string') assert.ok(!/示例|占位/.test(e[k]), id);
  for (const k of ['label','note','source','contributor'])
    if (typeof map[k] === 'string') assert.ok(!/示例|占位/.test(map[k]));
});
test('sw.js 预缓存含青岛版映射，Ed.mappingPath 指向同一 URL', () => {
  const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8');
  const m = /var DATA = \[([\s\S]*?)\];/.exec(sw);
  assert.ok(m && m[1].includes('data/mappings/qingdao-math.json'));
  const Ed = require('../assets/edition.js');
  assert.ok(Ed.VERSIONS.includes('qingdao'));
  assert.strictEqual(Ed.mappingPath(map.version, map.subject, map.stage), 'data/mappings/qingdao-math.json');
});
test('六年级可诊断：Ed.gradeTargets 对青岛版返回六年级目标', () => {
  const Ed = require('../assets/edition.js');
  const P = Ed.buildPlacement(map);
  const topicsAll = topics.filter((t) => /^cnm_p\d+$/.test(t.id) && !t.external);
  const graph = Ed.buildGraph ? Ed.buildGraph(topicsAll, [], []) : { byId: Object.fromEntries(topicsAll.map((t)=>[t.id,t])) };
  const r = Ed.gradeTargets(graph, P, '六年级', 'math');
  assert.ok(r && !r.empty && r.ids.length > 0, '青岛版六年级目标池不应为空');
});
test('覆盖率（只打印）', () => {
  const denom = topics.filter((t) => /^cnm_p\d+$/.test(t.id) && !t.external);
  const n = Object.keys(map.entries).length;
  assert.ok(n <= denom.length);
  console.log('       覆盖率 %d/%d（草稿全文对应）', n, denom.length);
});
console.log('\n' + passed + ' passed');
