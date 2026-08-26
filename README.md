# seizu-danmenzu（製図・断面図トレーニング）

機械製図の「断面図」の作図問題を、ブラウザ上で解いて自動採点できる学習 Web アプリ。
Google Apps Script（GAS）のウェブアプリとして構築する。

> 教科書の方眼付き作図問題（「次の図は機械部品の投影図である。(答)の箇所に指示された断面図をかきなさい。ハッチングもほどこしなさい。」）を、
> 紙と鉛筆の代わりに画面上で解き、その場で正誤と解説が返る形にする。

---

## 現在のステータス

| フェーズ | 状態 |
|---|---|
| Phase 0: 起案・立案／方針確定 | ✅ 完了 |
| **Phase 1: MVP（動く 1 問）** | ✅ 実装済み（実機確認とデプロイが残り） |
| Phase 2: 問題バンク | ⏳ 未着手 |
| Phase 3: 学習記録・作問ツール | ⏳ 未着手 |
| Phase 4: 断面図の種類の拡張 | ⏳ 未着手 |

Phase 1 でできること — 投影図（正面図・側面図・切断線 A-A）を見ながら、
方眼の格子点を結んで断面図を作図し、ハッチングを施して採点を受ける。
誤りは色分けで示され、JIS の規則名付きのフィードバックと解説が返る。

## 動かしてみる

**ブラウザだけで確認する**（GAS 不要）

```bash
node tools/build_preview.js          # build/preview.html を生成
node tools/build_preview.js build/demo.html --demo      # 誤答を入れて採点済みの状態
node tools/build_preview.js build/ans.html  --correct   # 正解を入れた状態
node tools/build_preview.js build/x.html --correct --problem=sec-a-003   # 問題を指定
```

生成された HTML をブラウザで開く。

**採点ロジックのテストと問題データの検算**

```bash
node tools/test_core.js
```

問題を追加・変更したら必ず走らせる。採点ロジックの単体テストに加えて、全問について
**外形線が「部品の外形」と「切り口」の輪郭の和集合になっているか**、
**穴のまわりが線で囲まれているか**、**側面図の外形線が断面図にも現れるか**などを検算する
（[04 §9](docs/04_データモデルと採点.md#9-問題データの検算作図の誤りを防ぐ仕組み)）。

**問題データを作り直す**

```bash
python3 tools/make_problems.py   # docs/samples/*.json と src/Problems.gs を再生成
```

問題は `tools/make_problems.py` に**部品の形状として**定義する。切り口をセル集合で書けば、
外形線とハッチング範囲は機械的に導出される（座標を手で並べると投影図と断面図が必ずずれる）。
`src/Problems.gs` は生成物なので直接編集しない。

**GAS へデプロイする**

```bash
npm install -g @google/clasp
clasp login
cp .clasp.json.example .clasp.json    # scriptId を記入
clasp push
clasp deploy -d "v0.1.0 MVP"
```

デプロイ設定は「実行するユーザー: 自分」「アクセスできるユーザー: 同じ組織内の全員」
（`appsscript.json` に記述済み）。

スクリプトプロパティ:

| キー | 既定 | 意味 |
|---|---|---|
| `RESULT_SHEET_ID` | 未設定 | 解答ログの記録先スプレッドシート ID。未設定でもアプリは動き、記録だけが行われない |
| `IDENTITY_MODE` | `auto` | 利用者の識別。`auto`／`google` は学校ドメインのメールを使い、取れなければ匿名へ。`anon` は常に匿名（メールを一切参照しない） |

---

## ドキュメント

| # | ドキュメント | 内容 |
|---|---|---|
| 01 | [企画書](docs/01_企画書.md) | 背景・目的・ターゲット・提供価値・KPI・スコープ・GAS 採用理由 |
| 02 | [要件定義](docs/02_要件定義.md) | ユースケース／機能要件／画面一覧／非機能要件／学習内容の範囲 |
| 03 | [設計方針](docs/03_設計方針.md) | システム構成／GAS ファイル構成／サーバ API／スプレッドシート設計／GAS 制約と対策 |
| 04 | [データモデルと採点方式](docs/04_データモデルと採点.md) | 座標系／線分の正規化／問題 JSON スキーマ／採点アルゴリズム／フィードバック規則 |
| 05 | [開発ロードマップ](docs/05_ロードマップ.md) | フェーズ計画／完了条件／リスク／決定事項 |

### 収録している問題

| ID | 題材 | レベル | 主に問う点 |
|---|---|---|---|
| [sec-a-001](docs/samples/sec-a-001.json) | L 形ブラケット | 2 | **リブは長手方向に切断してもハッチングを施さない**／手前面の座ぐり／切断線から外れた穴は現れない |
| [sec-a-002](docs/samples/sec-a-002.json) | T 形の台座 | 2 | 左右対称の切り口／柱と底板の段差／貫通穴で切り口が上下に分かれる |
| [sec-a-003](docs/samples/sec-a-003.json) | 段付き軸受 | 3 | 回転体の上下対称／段付き穴と外形の段差／正面図のかくれ線の読み取り |

問題は画面右上のセレクタで切り替えられる（`?p=sec-a-003` のように URL でも指定できる）。

### 決まっていること

- **解答方式は自由線描画方式** — 格子点どうしを結んで線を引き、線種（外形線・かくれ線・中心線）を選ぶ。
  ハッチングは領域をセル単位で指定する
- 引き方の違いを吸収するため、線分は**既約な刻み**へ分解し端点の順序をそろえて比較する。
  一気に引いても小刻みに引いても、逆向きに引いても同じ答えになる
- 採点は `60 × 線の一致度 + 40 × ハッチングの一致度 − 減点`。一致度は Jaccard 係数
- **利用者の識別は Google アカウントと匿名の両対応**。学校ドメインならメールを自動で使い、
  取れなければクラス・出席番号を申告する。採点は名前の入力を待たず、記録だけを保留する

---

## 技術スタック

- **サーバ**: Google Apps Script（`Code.gs` ほか）
- **画面**: HtmlService + 素の HTML/CSS/JS（フレームワークなし）、作図領域は **SVG**
- **データ**: Google スプレッドシート（解答ログ）、PropertiesService（設定）
- **開発**: [clasp](https://github.com/google/clasp) でローカル編集 → Git 管理 → `clasp push`

## ディレクトリ構成

```
.
├── README.md
├── docs/                     # 企画・設計ドキュメント
│   └── samples/              # 問題データのサンプル
├── src/                      # clasp のプッシュ対象
│   ├── appsscript.json
│   ├── Code.gs               # doGet / include / API エントリ
│   ├── Auth.gs               # 利用者の識別（Google アカウント／匿名の両対応）
│   ├── Problems.gs           # 問題データ（tools/make_problems.py が生成）
│   ├── ResultRepo.gs         # 解答ログの追記（LockService）
│   ├── index.html            # 画面テンプレート
│   ├── css.html
│   ├── js_core.html          # 線分の正規化と採点（GAS 非依存の素の JS）
│   ├── js_draw.html          # SVG 作図エンジン
│   └── js_app.html           # 画面の組み立てと配線
├── tools/
│   ├── test_core.js          # 採点ロジックの単体テストと問題データの検算
│   ├── build_preview.js      # GAS なしでブラウザ確認する HTML を生成
│   ├── problem_lib.py        # 切り口のセル集合から外形線を導く共通処理
│   └── make_problems.py      # 問題データの定義と生成
└── .clasp.json.example
```
