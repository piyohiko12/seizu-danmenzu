/**
 * 製図・断面図トレーニング — ウェブアプリのエントリポイント。
 *
 * クライアントから呼ぶ関数はこのファイルにだけ置き、実処理は各 Repo / Grader に委ねる。
 * 戻り値はすべて JSON 化可能な型に限る（google.script.run の制約）。
 */

function doGet(e) {
  var t = HtmlService.createTemplateFromFile('index');
  t.problemId = (e && e.parameter && e.parameter.p) || Problems.defaultId();
  return t.evaluate()
    .setTitle('製図・断面図トレーニング')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/** index.html から部分テンプレートを差し込む。 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/** 画面に表示する利用者の識別情報を返す（メールアドレスか、匿名モードの指示か）。 */
function apiGetIdentity() {
  try {
    return { ok: true, identity: Auth.identity() };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/** 問題の一覧を返す。正解データは含めない。 */
function apiGetProblemList() {
  try {
    return { ok: true, list: Problems.list() };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/** 問題を 1 問返す。Phase 1 では正解も同送し、採点はクライアントで行う。 */
function apiGetProblem(problemId) {
  try {
    var p = Problems.get(problemId);
    if (!p) return { ok: false, error: '問題が見つかりません: ' + problemId };
    return { ok: true, problem: p };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/**
 * 解答を記録する。採点結果はクライアントで算出したものを受け取る（Phase 1）。
 * Phase 3 でサーバ側の確定採点に差し替える。
 */
function apiSubmit(problemId, answer, result, meta) {
  try {
    return ResultRepo.append({
      problemId: problemId,
      answer: answer,
      result: result,
      meta: meta || {}
    });
  } catch (err) {
    // 記録に失敗しても採点結果の表示は妨げない。
    return { ok: false, logged: false, error: String(err) };
  }
}
