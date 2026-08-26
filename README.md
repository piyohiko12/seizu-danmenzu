# seizu-danmenzu（製図・断面図トレーニング）

機械製図の「断面図」の作図問題を、ブラウザ上で解いて自動採点できる学習 Web アプリ。
Google Apps Script（GAS）のウェブアプリとして構築する。

> 教科書の方眼付き作図問題（「次の図は機械部品の投影図である。(答)の箇所に指示された断面図をかきなさい。ハッチングもほどこしなさい。」）を、
> 紙と鉛筆の代わりに画面上で解き、その場で正誤と解説が返る形にする。

---

## 現在のステータス

| フェーズ | 状態 |
|---|---|
| **起案・立案（本ドキュメント一式）** | ✅ 完了 |
| 方針決定（下記「意思決定待ち」の確定） | ⏳ 未着手 |
| Phase 1: MVP 実装 | ⏳ 未着手 |

実装コードはまだありません。まずは企画・要件・設計を固めます。

---

## ドキュメント

| # | ドキュメント | 内容 |
|---|---|---|
| 01 | [企画書](docs/01_企画書.md) | 背景・目的・ターゲット・提供価値・KPI・スコープ・GAS 採用理由 |
| 02 | [要件定義](docs/02_要件定義.md) | ユースケース／機能要件／画面一覧／非機能要件／学習内容の範囲 |
| 03 | [設計方針](docs/03_設計方針.md) | システム構成／GAS ファイル構成／サーバ API／スプレッドシート設計／GAS 制約と対策 |
| 04 | [データモデルと採点方式](docs/04_データモデルと採点.md) | 座標系／問題 JSON スキーマ／解答 JSON／採点アルゴリズム／フィードバック規則 |
| 05 | [開発ロードマップ](docs/05_ロードマップ.md) | フェーズ計画／成果物／完了条件／リスク／意思決定待ち事項 |

サンプルデータ: [`docs/samples/problem_a_full_section.json`](docs/samples/problem_a_full_section.json)

---

## 技術スタック（予定）

- **サーバ**: Google Apps Script（`Code.gs` ほか）
- **画面**: HtmlService + 素の HTML/CSS/JS（フレームワークなし）、作図領域は **SVG**
- **データ**: Google スプレッドシート（問題マスタ／学習記録）、PropertiesService（設定）、CacheService（キャッシュ）
- **開発**: [clasp](https://github.com/google/clasp) でローカル編集 → Git 管理 → `clasp push`

## ディレクトリ構成（予定）

```
.
├── README.md
├── docs/                     # 企画・設計ドキュメント
├── src/                      # clasp のプッシュ対象
│   ├── appsscript.json
│   ├── Code.gs               # doGet / include / API エントリ
│   ├── ProblemRepo.gs        # 問題データの取得・キャッシュ
│   ├── Grader.gs             # 採点ロジック（サーバ側の正解判定）
│   ├── ResultRepo.gs         # 学習記録の読み書き
│   ├── index.html            # 画面テンプレート
│   ├── css.html
│   ├── js_app.html           # 画面制御
│   ├── js_canvas.html        # グリッド作図エンジン（SVG）
│   └── js_api.html           # google.script.run ラッパ
└── .clasp.json.example
```
