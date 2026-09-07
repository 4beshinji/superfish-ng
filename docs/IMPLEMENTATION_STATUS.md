# 実装・検証の現状

2026-09-08追記: [限定AF読込](LEGACY_INPUT.md)を追加。単一真空/全PEC/軸接続TMを
明示NG設定で変換し、原入力・位置・hash・意味の差を保存する。汎用旧入力互換は未完。
128テスト中126合格・2 skip、標準validateと保存AF2形状の周波数/RF照合PASS。

2026-09-07追記: C01の[v3モデル契約](MODEL_CONTRACT.md)を実装・受入済み。
明示physics/座標/単一真空材料・領域、能力表、v1/v2からの移行と旧hash維持、
Project/Study/GUIへの保持を追加。122テスト中120合格・2 skip、標準validate/GUI操作PASS。
以下の既存物理範囲は変わらず、追加物理は未受理。

確認日: 2026-09-07、製品コードの基準 `1f5cd84`。コードと受入記録を照合した。
作業checkoutは `/home/sin/code/agent/reserch/superfish-ng`。
古い記録の `/home/sin/code/superfish` は当時の場所で、今回移動やルートの作り直しは行わない。

## 現在提供する範囲

| 分野 | 実装・入口 | 制約 | 証拠 |
|---|---|---|---|
| 物理 | 真空、軸連結m=0 TM、PECまたは平坦z端の電気/磁気対称 | TE、平面RF、内導体、材料領域、静的場は未実装 | [PHYSICS.md](PHYSICS.md)、config.py/solver.py/symmetry.py |
| 幾何 | 折れ線、段差、z非減少の短円弧、部分の反復/端部組立 | 楕円・折返し・穴・任意CADなし | geometry.py/project.py、test_arcs.py/test_stepped_mesh.py/test_project.py |
| メッシュ | P1/P2場・直線三角形、局所実長細分、外部タグ付きJSON | 外部メッシュもCase輪郭内。外部meshのGUI/Study指定なし。P2はCLI/GUI・場/RF・保存/描画へ統合、曲線要素は未対応 | [MESH_INPUT.md](MESH_INPUT.md)、mesh.py/mesh_input.py |
| 固有値・場 | 実FEM、複数モード、残差・直交性・エネルギー検査 | 残差は離散化誤差保証でない。全モード探索/一般追跡なし | fem.py/solver.py、test_physics.py |
| RF量 | f/U/Q0/G/V/RQ/シャント/TTF、ピーク比、加速長/電圧区間/位相原点指定 | peak phasor、RQ二規約。常伝導摂動損失、EpkはP1/P2片側推定 | rf.py、[PHYSICS.md](PHYSICS.md)、[R01受入](ACCELERATING_CONVENTIONS.md) |
| 条件群 | 独立掃引、同一形状の細分対応、条件付きバンド同定 | 形状変化の追跡とtune/最適化は未実装 | studies.py、modes.py |
| 操作 | 共通Project/CLI/Python、ローカルGUI、保存場・図・プローブ | 外部メッシュ指定UIなし。人による使いやすさ評価は未実施 | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md) |
| 完了管理 | 管理ジョブと直接保存の完了公開/manifest、改変・中断検出 | ローカルhard link対応FS。電源断/他OSは未保証 | [SAVE_COMPLETION.md](SAVE_COMPLETION.md)、test_save_completion.py |
| 入出力 | NG JSON/CSV/NPZ/ASCII VTK、保存NG結果の再読込 | GUIの「旧結果取込」は以前のNG出力。旧SUPERFISH入力/バイナリ互換ではない | saved.py/cli.py、[INPUT_OUTPUT.md](INPUT_OUTPUT.md) |
| 配布 | source/wheelのローカル受入 | hosted CI、他OS、公開リリースは未確認 | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)、test_package.py |

ソース名は `src/superfish_ng/`、test名は `tests/` に対する表記。
NGSolveのP3/Hphiは独立検証スクリプトだけにあり、製品の高次要素対応に数えない。

## 検証の区別

| 種別 | 状態・範囲 | 記録 |
|---|---|---|
| 今回の基準unittest | 114件中112件PASS、NGSolve環境専用2件skip、4.834秒 | `.venv/bin/python -m unittest discover -s tests -v`、OPENBLAS_NUM_THREADS=1 |
| 直前の標準数値検証 | PASS。seed周波数差ゼロ、RF最大相対差6.67e-16 | out/validation-mesh-input-20260907、[MESH_INPUT.md](MESH_INPUT.md) |
| 独立NGSolve | 円筒/円錐台基本モード、両側3段階、f/RQ/G/内部Hphi、円筒解析PASS | [INDEPENDENT_COMPARISON.md](INDEPENDENT_COMPARISON.md) |
| Wine比較 | 基本3形状、演習17対象モードの既存照合。鋭角ピークは別検証 | [SUPERFISH_COMPARISON.md](SUPERFISH_COMPARISON.md)、[MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md) |
| GUI | G0〜G5技術的受入。今回ブラウザー検査を再実行していない | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md) |
| 実機測定 | 未検証 | 合成幾何・演習照合を測定検証に数えない |

文書だけの更新のため今回の標準validate再実行は不要とした。製品・テスト・数値基準の変更なし。
out/が別環境で欠けても、過去の実行記録と現在再現できる状態を区別する。

## 旧計画からの訂正

- P0-01〜03を完了へ移す。Gmsh直接読込・任意輪郭生成は含めない。
- P1-03は平坦z端に限り完了。P1-01より先に実装・検証済み。
- P1-02/04/06、P2-01/02は部分完了として残件を[BACKLOG.md](BACKLOG.md)に記す。
- P2-04はGUI範囲で完了。GUI完成を一般追跡・tune完成に読み替えない。
- P0-04の比較ADRとP1-05の実機参照は残す。未実施を根拠なく廃止/完了にしない。
- seed時の期間見積もりは進捗や互換対象を反映しないため現行納期として使わない。

旧版の挙動確認では、既存Wine記録のSFO表示7.17（2006-01-13）とインストーラー名7.20を分ける。
製品単位の版・入出力仕様を一括して「7.20完全互換」と扱わない。
