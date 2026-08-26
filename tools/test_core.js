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

/** 穴のセルをすべてまとめた集合。voids は穴の面ごとに分かれている。 */
function voidCells(p) {
  return p.authoring.voids.flatMap(v => v.cells);
}

/** 部品の外形（body）から、切断面で材料が無いセル（voids）を除いた切り口。 */
function cutOf(p) {
  const holes = new Set(voidCells(p).map(cellKey));
  return p.authoring.body.filter(c => !holes.has(cellKey(c)));
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
    const voids = new Set(voidCells(p).map(cellKey));
    const missing = [];
    voidCells(p).forEach(([c, r]) => {
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

  t(label + ': 穴の面どうしは重なっていない', () => {
    const seen = new Set(), dup = [];
    voidCells(p).forEach(c => {
      const k = cellKey(c);
      if (seen.has(k)) dup.push(k); else seen.add(k);
    });
    eq(dup, [], '重なっているセル');
  });

  t(label + ': 穴の面がそれぞれ長方形になっている', () => {
    // 穴の面は「同軸の円筒 1 段ぶん」＝ 奥行の範囲 × 直径 なので長方形になる。
    // 段付き穴をひとつの面にまとめると L 字などになり、ここで落ちる。
    const bad = [];
    p.authoring.voids.forEach(v => {
      const xs = v.cells.map(c => c[0]), ys = v.cells.map(c => c[1]);
      const w = Math.max(...xs) - Math.min(...xs) + 1;
      const h = Math.max(...ys) - Math.min(...ys) + 1;
      if (new Set(v.cells.map(cellKey)).size !== w * h) {
        bad.push(v.name + '(' + v.cells.length + 'セル, 外接' + w + 'x' + h + ')');
      }
    });
    eq(bad, [], '長方形でない穴の面');
  });

  t(label + ': 段差の線が大径側の全直径にわたっている', () => {
    // 宣言された半径から直接確かめる。穴の径が変わるところでは、
    // 大きいほうの直径いっぱいに段差の線が引かれていなければならない。
    const lines = new Set(p.answer.lines.map(s => SecCore.segKey(s[0], s[1])));
    const vs = p.authoring.voids.slice().sort((a, b) => a.z[0] - b.z[0]);
    const missing = [];
    for (let i = 0; i + 1 < vs.length; i++) {
      const a = vs[i], b = vs[i + 1];
      if (a.z[1] !== b.z[0]) continue;                       // 奥行がつながっていない
      const x = a.z[1];
      const cy = Math.min(...a.cells.map(c => c[1])) + a.r;  // 穴の中心の高さ
      const R = Math.max(a.r, b.r);
      for (let y = cy - R; y < cy + R; y++) {
        if (!lines.has(SecCore.segKey([x, y], [x, y + 1]))) missing.push(x + ',' + y);
      }
    }
    eq(missing, [], '段差の線の描き漏れ');
  });

  t(label + ': 径が変わる境目に線がある', () => {
    // ★ 穴の途中で径が変わると、切断面より奥に見える面が切り替わる。
    //    見える面が変われば稜線＝実線が現れる。しかもそれは大径側の全直径にわたる。
    //    面が違う穴セルどうしが接する辺には、必ず線がある。
    const lines = new Set(p.answer.lines.map(s => SecCore.segKey(s[0], s[1])));
    const owner = new Map();
    p.authoring.voids.forEach((v, i) => v.cells.forEach(c => owner.set(cellKey(c), i)));
    const missing = [];
    p.authoring.voids.forEach((v, i) => v.cells.forEach(([c, r]) => {
      [[[c, r], [c + 1, r], [c, r - 1], '上'],
       [[c, r + 1], [c + 1, r + 1], [c, r + 1], '下'],
       [[c, r], [c, r + 1], [c - 1, r], '左'],
       [[c + 1, r], [c + 1, r + 1], [c + 1, r], '右']
      ].forEach(([a, b, nb, name]) => {
        const j = owner.get(cellKey(nb));
        if (j !== undefined && j !== i && !lines.has(SecCore.segKey(a, b))) {
          missing.push('(' + c + ',' + r + ')' + name + '辺');
        }
      });
    }));
    eq(missing, [], '径が変わる境目の線の描き漏れ');
  });

  t(label + ': 外形線は「部品の外形」「切り口」「穴の面ごと」の輪郭の和集合になっている', () => {
    const expected = union(
      boundary(p.authoring.body),
      boundary(cutOf(p)),
      boundary(ribOf(p)),
      ...p.authoring.voids.map(v => boundary(v.cells.map(c => [c[0], c[1], 'F']))));
    const actual = new Set(p.answer.lines.map(s => SecCore.segKey(s[0], s[1])));
    const extra = [...actual].filter(k => !expected.has(k));
    const lack = [...expected].filter(k => !actual.has(k));
    eq(lack, [], '足りない線');
    eq(extra, [], '余分な線');
  });

  t(label + ': 切り口は「部品の外形 − 穴」と一致している', () => {
    eq(cutOf(p).map(cellKey).sort(), p.authoring.cut.map(cellKey).sort());
  });

  t(label + ': 断面図の外形は側面図にも現れる', () => {
    // 投影図と答えの突き合わせ。断面図の外形（部品のシルエット）は、
    // 側面図にも同じ位置に出るはず。片方だけ直すとここで落ちる。
    // 逆向き（側面図 ⊆ 断面図）は成り立たない。側面図には、切断面には材料が無い
    // ところで見えている稜線（柱の脇から見える底板の上面など）も現れるため。
    const side = p.views.find(v => v.name === '側面図');
    if (!side) return;
    const isInt = v => Number.isInteger(v);
    const have = new Set();
    side.lines.filter(s => s.kind === 'outline' || s.kind === 'hidden')
      .filter(s => [s.a[0], s.a[1], s.b[0], s.b[1]].every(isInt))
      .forEach(s => SecCore.split(s.a, s.b).forEach(u => have.add(SecCore.segKey(u[0], u[1]))));
    const missing = [...boundary(p.authoring.body)].filter(k => !have.has(k));
    eq(missing, [], '断面図にあって側面図に無い外形線');
  });

  t(label + ': 穴のセルにハッチングが掛かっていない', () => {
    const hatch = new Set(p.answer.hatch.map(c => c.join(',')));
    voidCells(p).forEach(c => ok(!hatch.has(cellKey(c)), '穴 ' + c + ' にハッチングが掛かっている'));
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
