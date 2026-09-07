# 実装・検証の現状

確認日: 2026-09-08。製品コード基準 `e68002f`。コードと最新の個別受入記録を照合した。
作業checkoutは `/home/sin/code/agent/reserch/superfish-ng`。
過去の `/home/sin/code/superfish` は当時の配置であり、移動やルートの作り直しは行わない。

## 互換計画の進捗

33親課題のうち、C01、限定C02、ローカルO01、native R01、N01、N02、G01、G02の
8件が記載範囲で.S/.I/.V受入済み。G03は部分実装・部分検証、C00は調査継続中。
他の親課題は未受入で、既存の掃引・GUI等を親課題全体の完了へ数えない。
X01は互換必須集合外の拡張候補。課題数は工数消化率や互換率ではない。
詳細と33件の区分は [COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md)。

## 現在提供する範囲

| 分野 | 実装・入口 | 制約・残件 | 証拠 |
|---|---|---|---|
| 物理 | 真空、軸接続m=0 TM、PEC・平坦z端の電気/磁気対称 | TE、平面RF、内導体、複数材料、静的場は未実装 | [PHYSICS.md](PHYSICS.md)、solver.py |
| 入力契約 | v3明示モデル、能力表、v1/v2移行、未対応指定の拒否 | 追加物理を受理する契約ではない | [MODEL_CONTRACT.md](MODEL_CONTRACT.md) |
| 幾何 | 折れ線・段差・短円弧、z折返し単一輪郭、native円/楕円/双曲線弧 | 穴・内導体・任意CADなし。接線候補は円錐曲線全体まで、有限弧制限/切詰め/構築UIは未実装 | [GENERAL_CONTOUR.md](GENERAL_CONTOUR.md)、[CONIC_GEOMETRY.md](CONIC_GEOMETRY.md)、[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md) |
| メッシュ・FEM | タグ付きJSON、品質条件付き自動生成、P1/P2、二次曲線写像、固定幾何細分 | 品質未達は拒否。二次境界は元の解析曲線の近似。適応誤差推定なし | [GENERAL_MESH.md](GENERAL_MESH.md)、[HIGH_ORDER_FIELDS.md](HIGH_ORDER_FIELDS.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 固有値・場 | 実FEM、複数モード、残差/直交性/エネルギー検査、物理座標プローブ | 残差は離散化誤差保証でない。全モード探索/一般追跡なし | solver.py、curved_solution.py、curved_sampling.py |
| RF・表面場 | f/U/Q0/G/V/RQ/シャント/TTF、加速長/区間/位相、P1/P2片側場、曲線連続離散極値と角診断 | peak phasor・RQ二規約。常伝導摂動損失。離散極値の囲い込みは物理ピーク収束を保証しない | [ACCELERATING_CONVENTIONS.md](ACCELERATING_CONVENTIONS.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 条件群・鏡映 | 掃引、同一形状細分比較、条件付きバンド同定、曲線の幾何/FEM別Study・鏡映 | 異形状の一般追跡、tune、制約付き最適化は未実装 | studies.py、symmetry.py、curved_reflection.py |
| 操作・保存 | 共通CLI/Python/GUI、曲線計算・描画・鏡映、完了公開/hash、再読込 | 外部メッシュ指定UIなし。人による使いやすさ評価、電源断/他OSは未保証 | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)、[SAVE_COMPLETION.md](SAVE_COMPLETION.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 旧入力・出力 | 限定AF読込、原入力/hash/変換診断、NG JSON/CSV/NPZ/ASCII VTK | AFは単一真空/全PEC/軸接続TM。汎用旧入力、製品用旧テキスト変換、旧バイナリ互換は未実装 | [LEGACY_INPUT.md](LEGACY_INPUT.md)、C03/C04 |
| 配布 | source/wheelの過去のローカル受入 | 最新全機能の配布再受入はV02。hosted CI、他OS、公開リリースは未確認 | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md) |

ソース名は `src/superfish_ng/` に対する表記。
GUIの「旧結果取込」は以前のNG出力であり、旧SUPERFISHバイナリの読込ではない。

## 検証の区別

| 種別 | 状態・範囲 | 記録 |
|---|---|---|
| 標準unittest | 310件中308合格・NGSolve参照環境専用2件skip。今回の文書同期でも再実行 | `.venv/bin/python -m unittest discover -s tests -v`、OPENBLAS_NUM_THREADS=1 |
| 標準数値回帰 | 直近記録PASS。接点返却値の再検査強化前の実行で、強化後は標準310件を再実行。FEM変更なし | out/validation-g03-conic-tangents-regression-20260908、[引継ぎ](CODEX_HANDOFF.md) |
| 曲線FEM | 球形独立参照、楕円/双曲線の3段階幾何近似・全6固定FEM比較・最終幾何間の場/RF比較PASS。初回FAIL保持 | [CURVED_ELEMENTS.md](CURVED_ELEMENTS.md)、out/validation-g03-native-geometry-separated-20260908 |
| 接線候補 | 円/楕円/双曲線全体の四次式・根分離・接点再構成の独立8検査PASS。有限弧への接続は未実装 | [TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md) |
| 独立NGSolve | 過去の円筒/円錐台基本モード、両側3段階、f/RQ/G/内部Hphi、円筒解析PASS | [INDEPENDENT_COMPARISON.md](INDEPENDENT_COMPARISON.md) |
| Wine比較 | 基本3形状と演習17対象モードの既存照合。限定AF読込は保存AF2形状から新規NG計算を照合。曲線全般の旧版照合ではない | [SUPERFISH_COMPARISON.md](SUPERFISH_COMPARISON.md)、[MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)、[LEGACY_INPUT.md](LEGACY_INPUT.md) |
| GUI | G0〜G5と後続個別受入。曲線鏡映は左右/両対称を含む11ブラウザー操作PASS | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 実機測定 | 未検証。合成幾何・演習照合を測定検証に数えない | V01 |

今回の同期は文書のみ。標準validate・ブラウザー・Wine計算は再実行せず、過去の記録として示した。
out/が別環境で欠けても、過去の実行と現在再現できる状態を区別する。

## 旧計画からの訂正

- P0-01〜03を完了へ移す。Gmsh直接読込・任意輪郭生成は含めない。
- P1-03は平坦z端に限り完了。P1-01より先に実装・検証済み。
- P1-02/04、P2-01/02は部分完了。P1-06はローカルO01範囲で完了。残件は[BACKLOG.md](BACKLOG.md)。
- P2-04はGUI範囲で完了。GUI完成を一般追跡・tune完成に読み替えない。
- P0-04の比較ADRとP1-05の実機参照は残す。未実施を根拠なく廃止/完了にしない。
- seed時の期間見積もりは進捗や互換対象を反映しないため現行納期として使わない。

旧版の挙動確認では、既存Wine記録のSFO表示7.17（2006-01-13）とインストーラー名7.20を分ける。
製品単位の版・入出力仕様を一括して「7.20完全互換」と扱わない。
