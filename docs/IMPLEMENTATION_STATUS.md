# 実装・検証の現状

[版3の表面量を含む適応停止](ADAPTIVE_SURFACE_STOPPING.md)をAPI/CLI/JobManagerへ追加。最後の2回の全域細分でf/RQ/Gと連続離散ピーク比上下界を別判定する。版1/版2は維持。版3のGUI統合・一般精度/効率は未完。

確認日: 2026-09-08。N04ピーク比を含む適応停止追加後（直前製品基準 `7645883`）。コードと最新の個別受入記録を照合した。
作業checkoutは `/home/sin/code/agent/reserch/superfish-ng`。
過去の `/home/sin/code/superfish` は当時の配置であり、移動やルートの作り直しは行わない。

## 互換計画の進捗

33親課題のうち、C01、限定C02、ローカルO01、native R01、N01、N02、G01、G02の
8件が記載範囲で.S/.I/.V受入済み。G03・D01・D02・N03・N04は部分実装・部分検証、C00は調査継続中。
他の親課題は未受入で、既存の掃引・GUI等を親課題全体の完了へ数えない。
X01は互換必須集合外の拡張候補。課題数は工数消化率や互換率ではない。
詳細と33件の区分は [COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md)。

## 現在提供する範囲

| 分野 | 実装・入口 | 制約・残件 | 証拠 |
|---|---|---|---|
| 物理 | 真空、軸接続m=0 TM、PEC・平坦z端の電気/磁気対称 | TE、平面RF、内導体、複数材料、静的場は未実装 | [PHYSICS.md](PHYSICS.md)、solver.py |
| 入力契約 | v3明示モデル、能力表、v1/v2移行、未対応指定の拒否 | 追加物理を受理する契約ではない | [MODEL_CONTRACT.md](MODEL_CONTRACT.md) |
| 幾何 | 折れ線・段差・短円弧、z折返し単一輪郭、native円/楕円/双曲線弧 | 穴・内導体・任意CADなし。有限弧の数値判定/明示選択G1接続APIと支持曲線接点区間APIあり。保存・Case/CLI/GUI接続済み。有限弧所属/fractionの区間APIあり。版2で位置誤差上界付き切詰めを統合済み。版3で固定直線と有限弧の接続/明示延長を統合。版4は指定半径の線分間フィレットを統合（接点/G1は数値検査）。版5/6は有限弧間/直線と弧のフィレットを接点位置上界付きで統合。G1は数値検査 | [GENERAL_CONTOUR.md](GENERAL_CONTOUR.md)、[CONIC_GEOMETRY.md](CONIC_GEOMETRY.md)、[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md) |
| メッシュ・FEM | タグ付きJSON、品質条件付き自動生成、P1/P2、二次曲線写像、固定幾何細分、選択直線要素の適合細分と係数移送 | 品質未達は拒否。二次境界は元の解析曲線の近似。残差指標/対象選択APIあり。f/RQ/G停止・保存再開API/CLI/JobManager/GUIあり。版3の表面量停止はAPI/CLI/JobManagerまで。物理誤差上界・曲線局所細分・版3 GUIは未実装 | [GENERAL_MESH.md](GENERAL_MESH.md)、[HIGH_ORDER_FIELDS.md](HIGH_ORDER_FIELDS.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md)、[MARKED_REFINEMENT.md](MARKED_REFINEMENT.md)、[RESIDUAL_INDICATOR.md](RESIDUAL_INDICATOR.md)、[ADAPTIVE_REFINEMENT.md](ADAPTIVE_REFINEMENT.md) |
| 固有値・場 | 実FEM、複数モード、残差/直交性/エネルギー検査、物理座標プローブ | 残差は離散化誤差保証でない。全モード探索/一般追跡なし | solver.py、curved_solution.py、curved_sampling.py |
| RF・表面場 | f/U/Q0/G/V/RQ/シャント/TTF、加速長/区間/位相、P1/P2片側場、直線/曲線の連続離散極値の囲い込み、曲線角診断 | peak phasor・RQ二規約。常伝導摂動損失。離散極値の囲い込みは物理ピーク収束を保証しない | [ACCELERATING_CONVENTIONS.md](ACCELERATING_CONVENTIONS.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 表面収束評価 | 固定曲線P2の3水準・追跡ID・ピーク上下界によるf/RQ/G/ピーク比判定API/CLI/GUI、元多角形角診断・追跡済み直線P1/P2の表面評価API/保存/CLI/GUI | 幾何近似誤差/一般形状/通常RF画面統合/版3適応停止GUIは残件。物理誤差上界ではない | [SURFACE_CONVERGENCE.md](SURFACE_CONVERGENCE.md) |
| 条件群・鏡映 | 掃引、同一形状細分比較、条件付きバンド同定、曲線の幾何/FEM別Study・鏡映 | D01は重み付き標本部分空間・円筒/profile写像・明示メッシュ対応による追跡と2時点保存/再検証CLI/GUIと個別IDと部分空間ID集合の順序付き履歴/再開、完了Studyの隣接点追跡と点状態表示・保存再検証GUI、追跡付き逐次計算・停止・チェックポイント再開API/CLI・JobManager・GUI、幾何掃引の適応二分と途中保存・再開API/CLI・JobManager・GUI、多対多の保守的ID集合継承とGUI方式選択/復元、同一多角形領域の独立再メッシュ比較API/CLI/GUIと明示アフィン変形の比較API/CLI/GUI、明示比較メッシュによる区分アフィン変形の比較API/CLI/GUIと同一二次曲線領域の比較API/CLI/GUIを追加。曲線P2の明示アフィン変形にも、変換後の二次境界全体が一致する条件で対応。曲線領域の一般写像/個別枝回復、制約付き最適化は未実装 | studies.py、symmetry.py、curved_reflection.py |
| 周波数調整 | 単一/連動profile座標・明示円筒/profile写像の1変数二分探索・停止・再開・最終細メッシュ判定API/CLI・JobManager・GUI、対象の場表示 | 全個別ID確認が前提。二水準差は誤差上界でない。曲線/非線形変数/最適化は未実装 | [TUNING.md](TUNING.md) |
| 操作・保存 | 共通CLI/Python/GUI、曲線計算・描画・鏡映、完了公開/hash、再読込 | 外部メッシュ指定UIなし。人による使いやすさ評価、電源断/他OSは未保証 | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)、[SAVE_COMPLETION.md](SAVE_COMPLETION.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 旧入力・出力 | 限定AF読込、原入力/hash/変換診断、NG JSON/CSV/NPZ/ASCII VTK | AFは単一真空/全PEC/軸接続TM。汎用旧入力、製品用旧テキスト変換、旧バイナリ互換は未実装 | [LEGACY_INPUT.md](LEGACY_INPUT.md)、C03/C04 |
| 配布 | source/wheelの過去のローカル受入 | 最新全機能の配布再受入はV02。hosted CI、他OS、公開リリースは未確認 | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md) |

ソース名は `src/superfish_ng/` に対する表記。
GUIの「旧結果取込」は以前のNG出力であり、旧SUPERFISHバイナリの読込ではない。

## 検証の区別

| 種別 | 状態・範囲 | 記録 |
|---|---|---|
| 標準unittest | 617件中615合格・NGSolve参照環境専用2件skip。N04版3表面量停止追加後に標準validate内で再実行 | `.venv/bin/python -m unittest discover -s tests -v`、OPENBLAS_NUM_THREADS=1 |
| 標準数値回帰 | N04版3表面量停止追加後PASS。seed周波数差ゼロ、RF/エネルギー差最大8.882e-16。FEM変更なし | out/validation-n04-surface-stop-20260908、[引継ぎ](CODEX_HANDOFF.md) |
| N04版3表面量停止 | 追加4検査PASS。独立円筒P1/P2×尺度1/2で五量の区間端点解析比較・相似則・全域確認2回がPASS。P1は10水準/39817自由度、P2は5水準/3853自由度。版3 GUIは未接続 | out/n04-surface-stop-initial-20260908、[仕様](ADAPTIVE_SURFACE_STOPPING.md) |
| N03直線表面評価GUI | 通信3検査・実Chrome16操作PASS。適応結果から別ID評価、確認待ち/達成/再入角/形状未確認/未収束、保存/再検証・対象順位2の場表示 | out/browser-affine-surface-initial-20260908、[操作](GUI_AFFINE_SURFACE_CONVERGENCE.md) |
| N03直線表面収束評価 | 元多角形角診断・全個別ID確認済み適応系列の五量区間比較・保存/CLIの5検査PASS。独立円筒P2は全域2回で達成、P1は上限/確認待ちを保持。解析五量/相似則PASS | out/n03-affine-surface-initial-20260908、[仕様](AFFINE_SURFACE_CONVERGENCE.md) |
| N03直線離散ピーク | P1/P2の厳密有理数辺多項式と上下界、native保存/CLI/改変拒否の5検査PASS。円筒P1/P2×尺度1/2×3メッシュのf/RF/ピーク比解析比較・相似則PASS | out/n03-affine-extrema-initial-20260908、[仕様](AFFINE_SURFACE_EXTREMA.md) |
| N04適応GUI | 通信4検査と実Chrome19操作PASS。開始/中止、全域確認途中と中止後の保存再開、個別差・対象順位2の場表示、厳密JSON入力 | out/browser-n04-refinement-strict-20260908、[操作仕様](GUI_ADAPTIVE_REFINEMENT.md) |
| N04適応JobManager | 版1/版2×尺度1/2の部分実行・再開・管理器再生成、解析P2円筒f/RQ/Gと相似則PASS | out/n04-refinement-gui-strict-physics-20260908、[仕様](ADAPTIVE_REFINEMENT_JOBS.md) |
| N04適応独立検証 | 版2全域確認は円筒P1/P2のRF改善・相似則・内積独立検査PASS。P1解析RQ差約0.056%、ただし48069 DOF。折返しは上限停止。版1のFAILも保持 | out/n04-rf-confirmation-initial-20260908、[適応計算](ADAPTIVE_REFINEMENT.md) |
| 曲線FEM | 球形独立参照、楕円/双曲線の3段階幾何近似・全6固定FEM比較・最終幾何間の場/RF比較PASS。初回FAIL保持 | [CURVED_ELEMENTS.md](CURVED_ELEMENTS.md)、out/validation-g03-native-geometry-separated-20260908 |
| 接線候補 | 円/楕円/双曲線全体の四次式・根分離・接点再構成の独立8検査PASS。有限弧数値判定/明示選択G1接続の追加9検査PASS。有限弧所属/fractionと位置誤差上界を製品操作へ統合済み。固定直線と弧の追加7検査PASS。線分間フィレット追加7検査PASS。中心軌跡区間/特異性分割の追加6検査PASS。有限領域交点の追加7検査PASS。版5の有限弧フィレット追加6検査PASS、保存/Case/CLI/GUIへ統合。版6の直線・弧フィレット追加6検査PASS、同じ製品経路へ統合。弧端/退化の厳密特殊ケース診断API/CLIの追加9検査PASS。構築診断の別保存/CLI/GUI・再検証に追加5検査とChrome11操作PASS。最小子午面半径制約の追加6検査PASS、保存/鏡映/構築/GUIを確認。極端な尺度の曲率/半径の追加4検査PASS。一般分類と退化候補構築は未完 | [TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md) |
| モード追跡 | 追跡核9件・2時点保存6件・履歴6件・部分空間継承5件・profile写像6件・明示メッシュ対応5件・合流/分裂6件・GUI接続5件・Study追跡6件・Study GUI接続3件・追跡付き実行6件・JobManager接続5件・逐次実行GUI接続3件・適応二分6件・適応再開5件・適応Job接続5件・適応GUI接続3件・多対多集合継承6件・同一領域再メッシュ6件・アフィン再メッシュ6件・区分アフィン再メッシュ5件・同一曲線領域6件PASS。解析交差/近接・縮退回転・曖昧停止・保存後の実FEM円筒交差・profile相似則/局所変更、明示メッシュ対応での折返し/曲線相似。同一曲線領域GUIを含むChrome35項目PASS。一般追跡全体の受入ではない | [MODE_TRACKING.md](MODE_TRACKING.md)、out/d01-cylinder-crossing-20260908 |
| 周波数調整 | tune核11検査・JobManager接続7検査・GUI接続3検査・連動座標6検査PASS。円筒TM011の順位3→2、二分探索16回＋細分1回、独立解析周波数/相似則・CLI停止再開/再検証PASS。実workerの停止/再開・管理器再起動・改変拒否と独立計算もPASS。連動指定を含むGUI19操作PASS。既存46操作は前回受入。二つの細分判定のFAIL保持 | [TUNING.md](TUNING.md)、out/d02-coupled-tuning-final-20260908 |
| 独立NGSolve | 過去の円筒/円錐台基本モード、両側3段階、f/RQ/G/内部Hphi、円筒解析PASS | [INDEPENDENT_COMPARISON.md](INDEPENDENT_COMPARISON.md) |
| Wine比較 | 基本3形状と演習17対象モードの既存照合。限定AF読込は保存AF2形状から新規NG計算を照合。曲線全般の旧版照合ではない | [SUPERFISH_COMPARISON.md](SUPERFISH_COMPARISON.md)、[MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)、[LEGACY_INPUT.md](LEGACY_INPUT.md) |
| GUI | G0〜G5と後続個別受入。曲線鏡映は左右/両対称を含む11ブラウザー操作PASS | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 実機測定 | 未検証。合成幾何・演習照合を測定検証に数えない | V01 |

版5有限弧フィレットの標準validateとChrome8操作はPASS。Wineは今回未実行。
版1〜5の実保存ファイルを再構築照合した。
過去の実行中docstring変更によるStudy失敗は引継ぎに保持。今回の検証中は実装を編集していない。
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
