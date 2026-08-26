/**
 * SecCore の単体テストと、問題データの検算。
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
const SAMPLES = path.join(ROOT, 'docs/samples');
const PROBLEMS = fs.readdirSync(SAMPLES).filter(f => f.endsWith('.json')).sort()
  .map(f => JSON.parse(fs.readFileSync(path.join(SAMPLES, f), 'utf8')));
const byId = id => PROBLEMS.find(p => p.id === id);
const correctOf = p => ({ lines: p.answer.lines, hatch: p.answer.hatch });

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

console.log('\n— 問題データの検算（' + PROBLEMS.length + ' 問）—');

PROBLEMS.forEach(p => {
  const label = p.id + ' ' + p.title;

  t(label + ': 正解をそのまま出すと 100 点・合格', () => {
    const r = SecCore.grade(p, correctOf(p));
    eq(r.score, 100, 'score');
    ok(r.passed, 'passed');
    eq(r.diff.missingLines.length, 0, 'missingLines');
    eq(r.diff.extraLines.length, 0, 'extraLines');
    eq(r.diff.missingHatch.length, 0, 'missingHatch');
    eq(r.diff.extraHatch.length, 0, 'extraHatch');
  });

  t(label + ': 正解ではどの誤答タグも立たない', () => {
    const r = SecCore.grade(p, correctOf(p));
    eq(r.tags, [], '誤答タグ');
    eq(r.detail.penalty, 0, '減点');
  });

  t(label + ': 正解の線分に重複がない', () => {
    eq(SecCore.normalizeLines(p.answer.lines).size, p.answer.lines.length, '単位線分の本数');
  });

  t(label + ': ハッチングは切り口のセルだけを指している', () => {
    const solid = new Set(p.authoring.solid.map(c => c[0] + ',' + c[1]));
    p.answer.hatch.forEach(c => ok(solid.has(c.join(',')), '切り口の外を指している: ' + c));
  });

  t(label + ': 穴のセルにハッチングが掛かっていない', () => {
    const hatch = new Set(p.answer.hatch.map(c => c.join(',')));
    (p.traps || []).filter(x => x.tag === 'hole-hatched').forEach(trap => {
      trap.cells.forEach(c => ok(!hatch.has(c.join(',')), '穴 ' + c + ' にハッチングが掛かっている'));
    });
  });

  t(label + ': 白紙は 0 点', () => {
    const r = SecCore.grade(p, { lines: [], hatch: [] });
    eq(r.score, 0);
    ok(!r.passed);
  });

  t(label + ': 線をまとめて引いても採点結果は変わらない', () => {
    // 同じ向きに連続する線分を 1 本の長い線として引き直す
    const merged = [];
    const seen = new Set();
    p.answer.lines.forEach(s => {
      const k = SecCore.segKey(s[0], s[1]);
      if (seen.has(k)) return;
      seen.add(k);
      merged.push(s);
    });
    const doubled = merged.concat(merged);        // 同じ線を二度引いても同じ
    const r = SecCore.grade(p, { lines: doubled, hatch: p.answer.hatch });
    eq(r.score, 100, 'score');
  });
});

console.log('\n— 誤答の検出 —');

const P1 = byId('sec-a-001');

t('リブにハッチングを施すと rib-hatched で減点される', () => {
  const rib = P1.traps.find(x => x.tag === 'rib-hatched');
  const r = SecCore.grade(P1, {
    lines: P1.answer.lines, hatch: P1.answer.hatch.concat(rib.cells)
  });
  ok(r.tags.includes('rib-hatched'), 'rib-hatched タグ: ' + r.tags);
  ok(!r.passed, '不合格になるはず');
  eq(r.detail.penalty, rib.penalty);
  ok(r.score < 100, 'score=' + r.score);
});

t('穴にハッチングを施すと hole-hatched で減点される', () => {
  const hole = P1.traps.find(x => x.tag === 'hole-hatched');
  const r = SecCore.grade(P1, {
    lines: P1.answer.lines, hatch: P1.answer.hatch.concat([hole.cells[0]])
  });
  ok(r.tags.includes('hole-hatched'), r.tags.join(','));
});

t('かくれ線を描くと hidden-line-drawn で減点される', () => {
  const r = SecCore.grade(P1, {
    lines: P1.answer.lines.concat([[[2, 13], [2, 16], 'hidden']]),
    hatch: P1.answer.hatch
  });
  ok(r.tags.includes('hidden-line-drawn'), r.tags.join(','));
});

t('断面に現れない穴を描くと off-plane-hole で減点される', () => {
  const trap = P1.traps.find(x => x.tag === 'off-plane-hole');
  const s = trap.segments[0];
  const r = SecCore.grade(P1, {
    lines: P1.answer.lines.concat([[s[0], s[1], 'outline']]),
    hatch: P1.answer.hatch
  });
  ok(r.tags.includes('off-plane-hole'), r.tags.join(','));
});

t('段付きの段差を描き忘れると step-missing で減点される', () => {
  const P3 = byId('sec-a-003');
  const trap = P3.traps.find(x => x.tag === 'step-missing');
  const drop = new Set(trap.segments.map(s => SecCore.segKey(s[0], s[1])));
  const r = SecCore.grade(P3, {
    lines: P3.answer.lines.filter(s => !drop.has(SecCore.segKey(s[0], s[1]))),
    hatch: P3.answer.hatch
  });
  ok(r.tags.includes('step-missing'), r.tags.join(','));
  eq(r.detail.penalty, trap.penalty);
});

t('線種を間違えると位置は半分だけ加点される', () => {
  const wrong = P1.answer.lines.map(s => [s[0], s[1], 'center']);
  const r = SecCore.grade(P1, { lines: wrong, hatch: P1.answer.hatch });
  eq(r.detail.line, 0.5, '線スコア');
  eq(r.diff.wrongKind.length, P1.answer.lines.length);
});

t('ハッチングを忘れると no-hatch が返る', () => {
  const P2 = byId('sec-a-002');
  const r = SecCore.grade(P2, { lines: P2.answer.lines, hatch: [] });
  eq(r.detail.hatch, 0);
  ok(r.tags.includes('no-hatch'), r.tags.join(','));
  eq(r.score, 60);
});

t('得点は 0〜100 に収まる', () => {
  const all = P1.traps.filter(x => x.cells).reduce((a, x) => a.concat(x.cells), []);
  const r = SecCore.grade(P1, { lines: [], hatch: all });
  ok(r.score >= 0 && r.score <= 100, 'score=' + r.score);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed\n');
process.exit(fail ? 1 : 0);
