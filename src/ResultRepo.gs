/**
 * 解答ログの記録。追記のみで、更新はしない（同時書き込みに強くするため）。
 *
 * 記録先のスプレッドシート ID はスクリプトプロパティ RESULT_SHEET_ID に置く。
 * 未設定でもアプリは動く（記録だけ行われない）。
 */
var ResultRepo = (function () {

  var PROP_KEY = 'RESULT_SHEET_ID';
  var SHEET_NAME = 'results';
  var HEADER = ['at', 'userKey', 'userMode', 'problemId', 'score', 'passed',
                'elapsedSec', 'hintUsed', 'errorTags', 'answer'];

  /**
   * 記録する識別子を決める。Google アカウントで識別できるならそれを使い、
   * 匿名モードのときは画面で申告されたクラス・出席番号を使う（D-2）。
   */
  function whoami(meta) {
    var id = Auth.identity();
    if (id.mode === 'google') return { key: id.email, mode: 'google' };
    var anon = meta && meta.anonKey ? String(meta.anonKey).slice(0, 60) : '';
    return { key: anon || '(unknown)', mode: 'anon' };
  }

  function sheet() {
    var id = PropertiesService.getScriptProperties().getProperty(PROP_KEY);
    if (!id) return null;
    var ss = SpreadsheetApp.openById(id);
    var sh = ss.getSheetByName(SHEET_NAME);
    if (!sh) {
      sh = ss.insertSheet(SHEET_NAME);
      sh.appendRow(HEADER);
    }
    return sh;
  }

  function append(rec) {
    var sh = sheet();
    if (!sh) return { ok: true, logged: false, reason: 'RESULT_SHEET_ID 未設定' };

    var lock = LockService.getScriptLock();
    if (!lock.tryLock(30000)) {
      return { ok: false, logged: false, error: '記録が混み合っています。もう一度お試しください。' };
    }
    try {
      var r = rec.result || {};
      var who = whoami(rec.meta);
      sh.appendRow([
        new Date().toISOString(),
        who.key,
        who.mode,
        rec.problemId,
        r.score == null ? '' : r.score,
        r.passed ? 'TRUE' : 'FALSE',
        rec.meta.elapsedSec == null ? '' : rec.meta.elapsedSec,
        rec.meta.hintUsed == null ? '' : rec.meta.hintUsed,
        (r.tags || []).join(','),
        JSON.stringify(rec.answer)
      ]);
      return { ok: true, logged: true };
    } finally {
      lock.releaseLock();
    }
  }

  return { append: append };
})();
