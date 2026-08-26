/**
 * GAS を使わずにブラウザで画面を確認するための HTML を組み立てる。
 *   node tools/build_preview.js [出力パス] [--demo]
 *
 * index.html のテンプレート構文（<?!= include('x') ?>）を解決し、
 * 問題データを window.__LOCAL_PROBLEM__ として埋め込む。
 * --demo を付けるとリブにハッチングを施した誤答を、--correct を付けると正解を流し込んで
 * 採点済みの状態にする（投影図と断面図の整合を目で確かめるのに使う）。
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const out = process.argv[2] || path.join(ROOT, 'build/preview.html');
const demo = process.argv.includes('--demo');
const correct = process.argv.includes('--correct');

const problem = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'docs/samples/problem_a_full_section.json'), 'utf8'));

let body = fs.readFileSync(path.join(ROOT, 'src/index.html'), 'utf8');
body = body.replace(/<\?!=\s*include\('([^']+)'\);?\s*\?>/g,
  (_, name) => fs.readFileSync(path.join(ROOT, 'src', name + '.html'), 'utf8'));
body = body.replace(/<\?!=\s*JSON\.stringify\(problemId\)\s*\?>/g, JSON.stringify(problem.id));

const demoScript = (demo || correct) ? `
<script>
  window.addEventListener('load', function () {
    setTimeout(function () {
      var app = window.__SEC_APP__;
      if (!app) return;
      var rib = app.problem.traps.find(function (t) { return t.tag === 'rib-hatched'; });
      var wrong = ${demo ? 'true' : 'false'};
      // demo は「線は正しいが、リブにもハッチングを施してしまった」誤答。correct は正解。
      app.sheet.setAnswer({
        lines: app.problem.answer.lines,
        hatch: wrong ? app.problem.answer.hatch.concat(rib.cells) : app.problem.answer.hatch
      });
      document.getElementById('btnGrade').click();
    }, 250);
  });
</script>` : '';

const html = `<!doctype html>
<html lang="ja">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>製図・断面図トレーニング（ローカル確認）</title></head>
<body>
<script>window.__SEC_TEST__ = true; window.__LOCAL_PROBLEM__ = ${JSON.stringify(problem)};</script>
${body}
${demoScript}
</body></html>
`;

fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, html);
console.log('wrote ' + out + (demo ? ' (demo)' : ''));
