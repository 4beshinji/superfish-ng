# ドキュメント索引

このリポジトリの文書は3種類に分かれます。目的に合う入口から読んでください。

| 目的 | 入口 |
|---|---|
| ソルバーの物理・数値仕様 | [PHYSICS.md](PHYSICS.md) |
| 何がどの入口で使えるか | [ARCHITECTURE.md](ARCHITECTURE.md)（[物理別入口表](ARCHITECTURE.md#rf固有問題)） |
| 入力・保存・メッシュの形式 | [MODEL_CONTRACT.md](MODEL_CONTRACT.md)、[INPUT_OUTPUT.md](INPUT_OUTPUT.md)、[MESH_INPUT.md](MESH_INPUT.md)、[GENERAL_MESH.md](GENERAL_MESH.md) |
| GUI の操作 | [GUI_GUIDE.md](GUI_GUIDE.md) |
| 検証の再現と解釈 | [VALIDATION_REPORT.md](VALIDATION_REPORT.md)、[INDEPENDENT_COMPARISON.md](INDEPENDENT_COMPARISON.md)、[TESTING.md](TESTING.md) |
| 環境・依存・配布 | [DEPENDENCIES.md](DEPENDENCIES.md) |
| 来歴・文献・参照制限 | [PROVENANCE.md](PROVENANCE.md)、[RESEARCH.md](RESEARCH.md)、[REFERENCES.md](REFERENCES.md) |

## 1. 製品文書

ソフトウェアの使い方・仕様・根拠を説明する文書です。外部読者向け。

| 文書 | 内容 |
|---|---|
| [PHYSICS.md](PHYSICS.md) | 軸上処理・弱形式・境界条件・RF量の定義と現行経路 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | モジュール責務、物理別の入口・保存・操作の対応表、ADR |
| [MODEL_CONTRACT.md](MODEL_CONTRACT.md) | v1/v2/v3 入力の物理・材料・領域の共通契約 |
| [INPUT_OUTPUT.md](INPUT_OUTPUT.md) / [SAVE_COMPLETION.md](SAVE_COMPLETION.md) | JSON入出力仕様と保存結果の完了公開契約 |
| [MESH_INPUT.md](MESH_INPUT.md) / [GENERAL_MESH.md](GENERAL_MESH.md) / [EXTERNAL_MESH_WORKFLOW.md](EXTERNAL_MESH_WORKFLOW.md) | 境界タグ付きメッシュ入力、一般輪郭のメッシュ生成、外部メッシュの運用 |
| [GUI_GUIDE.md](GUI_GUIDE.md) | ローカルGUIの操作手順 |
| [DEPENDENCIES.md](DEPENDENCIES.md) | 依存・ライセンス・再現環境・配布方針 |
| [VALIDATION_REPORT.md](VALIDATION_REPORT.md) / [INDEPENDENT_COMPARISON.md](INDEPENDENT_COMPARISON.md) / [SUPERFISH_COMPARISON.md](SUPERFISH_COMPARISON.md) / [WINE_REFERENCE_ENVIRONMENT.md](WINE_REFERENCE_ENVIRONMENT.md) | 初期検証報告、NGSolve独立照合、Wine版SUPERFISHとの限定照合とその環境 |
| [PROVENANCE.md](PROVENANCE.md) / [RESEARCH.md](RESEARCH.md) / [REFERENCES.md](REFERENCES.md) / [references.bib](references.bib) | 参照制限・参照履歴、事前調査と採用判断、注釈付き文献 |

## 2. 開発計画・台帳（内部）

開発の現在地と計画を管理する文書です。貢献者向け。

| 文書 | 内容 |
|---|---|
| [development-plan/CURRENT.md](development-plan/CURRENT.md) | 最新の現在地（次の着手・依存待ち・受入証拠） |
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | 日付ごとの実装履歴（append-only） |
| [BACKLOG.md](BACKLOG.md) | 作業カードの実装と受入の記録（append-only） |
| [development-plan/](development-plan/README.md) | 未完課題のコミット単位開発計画と作業カード一覧 |
| [ROADMAP.md](ROADMAP.md) | 長期目標・段階と終了条件 |
| [COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md) / [COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md) | 互換目標の対応表と作業分割 |
| [REFACTORING_PLAN.md](REFACTORING_PLAN.md) / [REFACTORING_ACCEPTANCE.md](REFACTORING_ACCEPTANCE.md) | 科学レビュー後の修正計画と受入 |
| [CAPABILITY_INVENTORY.md](CAPABILITY_INVENTORY.md) | 実装済み能力の整合表 |
| [TESTING.md](TESTING.md) | 変更別の検証選択手順と実行記録 |
| [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) / [CODEX_HANDOFF.md](CODEX_HANDOFF.md) | ローカル開発手順、作業引き継ぎ |
| [IMPLEMENTATION_REVIEW_2026-09-22.md](IMPLEMENTATION_REVIEW_2026-09-22.md) / [SCIENTIFIC_REVIEW_2026-10-13.md](SCIENTIFIC_REVIEW_2026-10-13.md) / [reviews/](reviews/) | 横断レビューとその証拠 |

## 3. 受入・実行記録（append-only、docs直下の大半）

docs直下の大部分は、作業カードごとの記録です。正本ではなく記録時点の証拠であり、
失敗・未達も保存する運用のため、新旧・成否はファイル名ではなく台帳の該当行で確認します。

| 種類 | 例 | 趣意 |
|---|---|---|
| 実装前の仕様 | `*_PLAN.md` | 作業カードの対象・条件・受入基準の宣言 |
| 受入記録 | `*_ACCEPTANCE.md` | 実装後の条件別検証結果と限界 |
| 実行・再生・費用 | `*_SAVED.md`、`*_REPLAY.md`、`*_RESUME.md`、`*_WORKER.md`、`*_JOBS.md`、`*_TUNING.md` など | 固定条件下での実行・再開・計測の記録 |
| 専用機能の仕様 | `AXIS_*`、`PLANAR_*`、`CURVED_*`、`MATERIAL_*`、`TE_*` など | 専用入口（静的場・平面・曲線・材料・TE）の版付き契約 |
| 例題の演習記録 | `SEMINAR_*.md` | セミナー例題の計算・図・比較 |

読み方:

- **ある機能が今使えるか** — [ARCHITECTURE.md](ARCHITECTURE.md#rf固有問題) の入口表と `superfish-ng capabilities`。
- **ある受入の証拠** — 台帳（[BACKLOG.md](BACKLOG.md)・[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)）の該当行からリンク先を追う。
- **最新の進行中作業** — [development-plan/CURRENT.md](development-plan/CURRENT.md)。

## セッション記録の運用

セッションの進捗・受入は台帳クラスの文書（IMPLEMENTATION_STATUS.md、BACKLOG.md、
PROVENANCE.md、development-plan/）へ追記します。README.md とこの索引には載せません。
外部読者向けに現状を伝える必要があるときは、機能表・対応表・この索引を更新します。
