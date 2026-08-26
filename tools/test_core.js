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

// ── 問題データの検算に使う、生成ツールとは独立した実装 ────────────────
// tools/problem_lib.py と同じ結果になるはずのものを JS 側で書き直しておく。
// 片方だけを直しても検算が通らないので、思い込みで壊しにくくなる。
const SHAPES = {
  F:  (x, y) => [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]],
  BL: (x, y) => [[x, y], [x, y + 1], [x + 1, y + 1]],
  BR: (x, y) => [[x, y + 1], [x + 1, y + 1], [x + 1, y]],
  TR: (x, y) => [[x, y], [x + 1, y], [x + 1, y + 1]],
  TL: (x, y) => [[x, y], [x + 1, y], [x, y + 1]],
};

/** セル集合の外周（1 回しか現れない辺）を位置キーの集合で返す。 */
function boundary(cells) {
  const n = new Map();
  cells.forEach(([c, r, sh]) => {
    const pl = SHAPES[sh](c, r);
    for (let i = 0; i < pl.length; i++) {
      const k = SecCore.segKey(pl[i], pl[(i + 1) % pl.length]);
      n.set(k, (n.get(k) || 0) + 1);
    }
  });
  return new Set([...n].filter(([, v]) => v === 1).map(([k]) => k));
}

const union = (...sets) => new Set(sets.flatMap(s => [...s]));
const cellKey = c => c[0] + ',' + c[1];

/** 部品の外形（body）から、切断面で材料が無いセル（voids）を除いた切り口。 */
function cutOf(p) {
  const voids = new Set(p.authoring.voids.map(cellKey));
  return p.authoring.body.filter(c => !voids.has(cellKey(c)));
}

/** リブなど「シルエットには出ないが描く輪郭」のセル。 */
function ribOf(p) {
  const trap = (p.traps || []).find(t => t.tag === 'rib-hatched');
  if (!trap) return [];
  const keys = new Set(trap.cells.map(cellKey));
  return p.authoring.body.filter(c => keys.has(cellKey(c)));
}

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
    const cut = new Set(cutOf(p).map(cellKey));
    p.answer.hatch.forEach(c => ok(cut.has(cellKey(c)), '切り口の外を指している: ' + c));
  });

  t(label + ': 穴のまわりが線で囲まれている', () => {
    // ★ 断面図は切り口だけを描く図ではない。穴が部品を分断していない限り、
    //    穴の向こう側の内壁が見えるので、外形線は穴の位置でも途切れない。
    //    つまり穴の領域は、隣の穴セルと接する辺を除いて、必ず線で囲まれている。
    //    隣が切り口なら穴の縁、隣が部品の外なら外形線として現れる。
    const lines = new Set(p.answer.lines.map(s => SecCore.segKey(s[0], s[1])));
    const voids = new Set(p.authoring.voids.map(cellKey));
    const missing = [];
    p.authoring.voids.forEach(([c, r]) => {
      [[[c, r], [c + 1, r], [c, r - 1], '上'],
       [[c, r + 1], [c + 1, r + 1], [c, r + 1], '下'],
       [[c, r], [c, r + 1], [c - 1, r], '左'],
       [[c + 1, r], [c + 1, r + 1], [c + 1, r], '右']
      ].forEach(([a, b, nb, name]) => {
        if (!voids.has(cellKey(nb)) && !lines.has(SecCore.segKey(a, b))) {
          missing.push('(' + c + ',' + r + ')' + name + '辺');
        }
      });
    });
    eq(missing, [], '穴のまわりの線の描き漏れ');
  });

  t(label + ': 外形線は「部品の外形」と「切り口」の輪郭の和集合になっている', () => {
    const expected = union(boundary(p.authoring.body), boundary(cutOf(p)), boundary(ribOf(p)));
    const actual = new Set(p.answer.lines.map(s => SecCore.segKey(s[0], s[1])));
    const extra = [...actual].filter(k => !expected.has(k));
    const lack = [...expected].filter(k => !actual.has(k));
    eq(lack, [], '足りない線');
    eq(extra, [], '余分な線');
  });

  t(label + ': 切り口は「部品の外形 − 穴」と一致している', () => {
    eq(cutOf(p).map(cellKey).sort(), p.authoring.cut.map(cellKey).sort());
  });

  t(label + ': 側面図の外形線は断面図にも現れる', () => {
    // 投影図と答えの突き合わせ。切断面より奥の見え掛かり線は、
    // 側面図と断面図で同じ位置に出るはず。片方だけ直すとここで落ちる。
    const ans = new Set(p.answer.lines.map(s => SecCore.segKey(s[0], s[1])));
    const side = p.views.find(v => v.name === '側面図');
    if (!side) return;
    const missing = [];
    side.lines.filter(s => s.kind === 'outline').forEach(s => {
      SecCore.split(s.a, s.b).forEach(u => {
        const k = SecCore.segKey(u[0], u[1]);
        if (!ans.has(k)) missing.push(k);
      });
    });
    eq(missing, [], '側面図にあって断面図に無い外形線');
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
