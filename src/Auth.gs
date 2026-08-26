/**
 * 利用者の識別（D-2: Google アカウント／匿名の両対応）。
 *
 * このアプリは「実行するユーザー: 自分（スクリプト所有者）」でデプロイする（D-3）。
 * この構成では Session.getActiveUser().getEmail() は
 *   * 閲覧者が所有者と同じ Google Workspace ドメインにいる → そのメールアドレスを返す
 *   * それ以外（個人アカウント、一般公開）                → 空文字を返す
 * という挙動になる。空文字が返るときは匿名モード（クラス・出席番号の入力）へ落とす。
 *
 * スクリプトプロパティ IDENTITY_MODE で明示的に切り替えられる。
 *   auto（既定）… メールが取れれば Google、取れなければ匿名
 *   google      … auto と同じ（意図を明示したいとき用）
 *   anon        … 常に匿名。メールを一切保存しない
 */
var Auth = (function () {

  var PROP_MODE = 'IDENTITY_MODE';

  function configuredMode() {
    var v = PropertiesService.getScriptProperties().getProperty(PROP_MODE);
    return (v === 'anon' || v === 'google') ? v : 'auto';
  }

  function googleEmail() {
    try {
      return Session.getActiveUser().getEmail() || '';
    } catch (err) {
      return '';
    }
  }

  /** @return {{mode: string, email: string}} mode は 'google' か 'anon' */
  function identity() {
    if (configuredMode() !== 'anon') {
      var email = googleEmail();
      if (email) return { mode: 'google', email: email };
    }
    return { mode: 'anon', email: '' };
  }

  return { identity: identity, configuredMode: configuredMode };
})();
