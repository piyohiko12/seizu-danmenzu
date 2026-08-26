/**
 * SecCore の単体テスト。
 *   node tools/test_core.js
 *
 * src/js_core.html から <script> の中身を取り出して評価する（GAS 側と同じコードを検証する）。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');

function loadCore() {
  const html = fs.readFileSync(path.join(ROOT, 'src/js_core.html'), 'utf8');
  const code = html.replace(/^[\s\S]*?<script>/, '').replace(/<\/script>[\s\S]*$/, '');
  const ctx = { module: { exports: {} }, console };
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  return ctx.SecCore;
}

const SecCore = loadCore();
const PROBLEM = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'docs/samples/problem_a_full_section.json'), 'utf8'));

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}
function eq(actual, expected, what) {
  const a = JSON.stringify(actual), b = JSON.stringify(expected);
  if (a !== b) throw new Error((what || '') + ' expected ' + b + ' but got ' + a);
}
function ok(cond, what) { if (!cond) throw new Error(what || 'expected truthy'); }

console.log('\n— 線分の正規化 —');

t('縦線は単位線分へ分解される', () => {
  eq(SecCore.split([0, 0], [0, 3]).length, 3);
});

t('45°線は単位線分へ分解される', () => {
  eq(SecCore.split([2, 9], [6, 13]),
     [[[2,9],[3,10]], [[3,10],[4,11]], [[4,11],[5,12]], [[5,12],[6,13]]]);
});

t('引く向きが逆でも同じキーになる', () => {
  eq(SecCore.segKey([3, 1], [0, 1]), SecCore.segKey([0, 1], [3, 1]));
});

t('一気に引いても小刻みに引いても同じ集合になる', () => {
  const a = SecCore.normalizeLines([[[0, 0], [0, 4], 'outline']]);
  const b = SecCore.normalizeLines([
    [[0, 0], [0, 1], 'outline'], [[0, 1], [0, 3], 'outline'], [[0, 3], [0, 4], 'outline']]);
  eq([...a.keys()].sort(), [...b.keys()].sort());
});

t('長さゼロの線は無視される', () => {
  eq(SecCore.split([2, 2], [2, 2]).length, 0);
});

t('既約でない斜線は最大公約数で刻まれる', () => {
  eq(SecCore.split([0, 0], [4, 2]), [[[0,0],[2,1]], [[2,1],[4,2]]]);
});

console.log('\n— 採点 —');

const CORRECT = { lines: PROBLEM.answer.lines, hatch: PROBLEM.answer.hatch };

t('正解をそのまま出すと 100 点・合格', () => {
  const r = SecCore.grade(PROBLEM, CORRECT);
  eq(r.score, 100, 'score');
  ok(r.passed, 'passed');
  eq(r.diff.missingLines.length, 0);
  eq(r.diff.extraLines.length, 0);
});

t('線をまとめて引いても 100 点になる（正規化が効いている）', () => {
  // 底板の下辺 6 本を 1 本の長い線として引く
  const merged = PROBLEM.answer.lines.filter(
    s => !(s[0][1] === 16 && s[1][1] === 16));
  merged.push([[0, 16], [6, 16], 'outline']);
  const r = SecCore.grade(PROBLEM, { lines: merged, hatch: PROBLEM.answer.hatch });
  eq(r.score, 100, 'score');
});

t('白紙は 0 点', () => {
  const r = SecCore.grade(PROBLEM, { lines: [], hatch: [] });
  eq(r.score, 0);
  ok(!r.passed);
});

t('リブにハッチングを施すと rib-hatched で減点される', () => {
  const rib = PROBLEM.traps.find(x => x.tag === 'rib-hatched');
  const r = SecCore.grade(PROBLEM, {
    lines: PROBLEM.answer.lines,
    hatch: PROBLEM.answer.hatch.concat(rib.cells)
  });
  ok(r.tags.includes('rib-hatched'), 'rib-hatched タグ: ' + r.tags);
  ok(!r.passed, '不合格になるはず');
  eq(r.detail.penalty, rib.penalty);
  ok(r.score < 100, 'score=' + r.score);
});

t('貫通穴にハッチングを施すと hole-hatched で減点される', () => {
  const r = SecCore.grade(PROBLEM, {
    lines: PROBLEM.answer.lines, hatch: PROBLEM.answer.hatch.concat([[0, 5], [1, 5]])
  });
  ok(r.tags.includes('hole-hatched'), r.tags.join(','));
});

t('かくれ線を描くと hidden-line-drawn で減点される', () => {
  const r = SecCore.grade(PROBLEM, {
    lines: PROBLEM.answer.lines.concat([[[2, 13], [2, 16], 'hidden']]),
    hatch: PROBLEM.answer.hatch
  });
  ok(r.tags.includes('hidden-line-drawn'), r.tags.join(','));
});

t('断面に現れない穴を描くと off-plane-hole で減点される', () => {
  const trap = PROBLEM.traps.find(x => x.tag === 'off-plane-hole');
  const s = trap.segments[0];
  const r = SecCore.grade(PROBLEM, {
    lines: PROBLEM.answer.lines.concat([[s[0], s[1], 'outline']]),
    hatch: PROBLEM.answer.hatch
  });
  ok(r.tags.includes('off-plane-hole'), r.tags.join(','));
});

t('座ぐり部分は切り口に含まれない（正解データの検算）', () => {
  const hole = PROBLEM.traps.find(x => x.tag === 'hole-hatched');
  const hatch = new Set(PROBLEM.answer.hatch.map(c => c.join(',')));
  hole.cells.forEach(c => ok(!hatch.has(c.join(',')), 'ハッチング対象に穴 ' + c + ' が混じっている'));
});

t('線種を間違えると位置は半分だけ加点される', () => {
  const wrong = PROBLEM.answer.lines.map(s => [s[0], s[1], 'center']);
  const r = SecCore.grade(PROBLEM, { lines: wrong, hatch: PROBLEM.answer.hatch });
  eq(r.detail.line, 0.5, '線スコア');
  eq(r.diff.wrongKind.length, PROBLEM.answer.lines.length);
});

t('ハッチングを忘れると no-hatch が返る', () => {
  const r = SecCore.grade(PROBLEM, { lines: PROBLEM.answer.lines, hatch: [] });
  eq(r.detail.hatch, 0);
  ok(r.tags.includes('no-hatch'), r.tags.join(','));
  eq(r.score, 60);
});

t('得点は 0〜100 に収まる', () => {
  const all = PROBLEM.traps.filter(x => x.cells).reduce((a, x) => a.concat(x.cells), []);
  const r = SecCore.grade(PROBLEM, { lines: [], hatch: all });
  ok(r.score >= 0 && r.score <= 100, 'score=' + r.score);
});

t('問題データの正解に重複した線分がない', () => {
  const m = SecCore.normalizeLines(PROBLEM.answer.lines);
  eq(m.size, PROBLEM.answer.lines.length, '単位線分の本数');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed\n');
process.exit(fail ? 1 : 0);
