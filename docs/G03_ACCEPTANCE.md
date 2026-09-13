# G03 要件と受入証拠の照合

2026-09-14 JST：[有理支持の異なる円・直線の有限交点診断](FINITE_CIRCULAR_CROSSINGS.md)を追加受入。
弧端の厳密一致と0/1/2中心、旧保存版1〜4、新版5、元構築保持を関連49テスト・
独立4,896条件・Chrome初回/再起動48チェック24取得で確認。一般の無理支持円/
非円楕円・双曲線の重解/全弧端、新候補構築、物理ピーク収束とG03全体は未完。

2026-09-13 UTC：[有限オフセット診断の区切り](G03_FINITE_OFFSETS_CHECKPOINT.md)を主ツリーへ統合・限定受入。
同一支持円の全候補周期・任意二進回転と、同じ非円楕円/同枝双曲線の反射自己接点を分類する。新規診断版4と旧保存版1/2/3を別の規則で再検証し、元構築・Case・適用可否を保持する。
独立20496条件、実Chromeの初回/実サーバー再起動で46入力・計292チェック/182取得と保存バイト一致、9画像の目視がPASS。数値907sourceを保持した最終909sourceを主915sourceへ統合。標準1456件（1453合格・任意NGSolve参照2件/HTTP sandbox 1件の計3skip）が718.595秒でPASS。主統合後の専用41unitも6.443秒でPASS。既存seed9モード19量の最大相対差は周波数0、全量8.882e-16。許容差・ベンチマークは不変。
G03全体・対象版C00.V・利用者業務V02・全計画は未完。親33=8受入/17進行/7他未受入/1範囲外を維持する。

2026-09-08、極端な尺度の曲率評価修正時。G03は**部分受入**。
本表は[計画](COMPATIBILITY_PLAN.md)のG03行と[幾何仕様](CONIC_GEOMETRY.md)の
番号付き5段階を照合する。実装の存在、限定検証、全要件の完了を区別する。
過去のout/は実行記録として読み直したもので、今回同じ比較を再実行したという意味ではない。

| 要件 | 現在の実装と直接の証拠 | 判定・不足 |
|---|---|---|
| 1. 円/楕円/双曲線の点・接線・曲率・弦誤差・面積 | conics.py、test_conics.pyの陰関数/接線/曲率/頂点半径、尺度・鏡映・面積・弦誤差 | native数学表現を限定受入。旧NT=2/3の全指定との同一性は未証明 |
| 2. 接線連続性、正半径/軸接続、交差/接触/隙間 | check_curve_join、curve_bounds.py、curved_contour.py、test_curved_contour.pyの不正位相/隙間/タグ/向き拒否 | 完成輪郭の検査を限定受入。工程上の全フィレット構築を意味しない |
| 3. 元曲線/弦許容差のCase・保存・GUI | test_curved_case.py、test_curved_saved.pyの保存往復/改変拒否、GUI_ACCEPTANCE.mdの曲線入力/保存操作 | 通常経路を限定受入。版5で有限弧同士のフィレットも接続。版6で直線と弧のフィレット・明示延長も接続 |
| 4. 曲線写像、正Jacobian、整合FEM/場/RF/保存 | curved_fem/space/solution/rf/sampling/saved。test_curved_fem.pyの物理線形場、test_curved_solution.pyのエネルギー、test_curved_rf.pyの独立円柱壁積分、test_curved_saved.py | 二次写像/二次場を限定受入。解析楕円そのものを厳密表現するという主張ではない |
| 5. 幾何/FEM別細分の周波数/場/RF | test_curved_refinement.pyの写像/勾配制限とGalerkinエネルギー同一性。out/validation-g03-native-geometry-separated-20260908/comparison.jsonを読み直しstatus=PASSを確認 | 球形独立参照と記録済み楕円/双曲線系列を限定受入。全新規構築形状の収束や物理ピーク保証へ一般化しない |
| 曲率・最小丸め半径 | 各プリミティブminimum_radius_m、test_conic_scale.pyの極端な尺度/Decimal参照4検査、版4の指定半径/1/R曲率/過大半径拒否、test_line_fillet.py | [minimum_meridional_radius_m](MERIDIONAL_RADIUS.md)でPEC曲線内部の区間上界とPEC-PECのG1数値検査を課す。追加6検査、Case/保存/鏡映/構築/Chrome11操作を部分受入。周方向主曲率・物理ピーク保証ではない |
| 有限弧同士の共通接線 | conic_tangents/certified_arcs/certified_construction、版2保存/CLI/GUI。test_certified_construction.py | 所属/fraction/位置誤差上界を受入。G1角度は数値検査 |
| 固定直線と有限弧 | line_arc_tangent、版3、test_line_arc_tangent.py、既存Chrome8操作 | 支持直線を固定する限定接続を受入。非接線の自動補正とは区別 |
| 指定半径の線分間フィレット | line_fillet、版4、test_line_fillet.py、out/gui-line-fillet-browser-20260908/report.jsonのpassed=true/8操作を再確認 | 有向小円弧を限定受入。接点/有限範囲/G1は数値検査 |
| 円錐曲線弧を含むフィレット | normal_offsets.pyで法線方向の中心軌跡/導関数を有理数区間で囲み、正則/反転/潰れ/未確認を全有限区間に保持。offset_intersections.pyの孤立交点認証からconic_fillet.pyで接点/切詰め/位置上界付き構築へ接続。版5保存/Case/CLI/GUIとtest_conic_fillet.py、Chrome8操作PASS | 版6の直線と弧もtest_line_conic_fillet.py/Chrome8操作で部分受入。弧端/重解/無限解の追加分類と各形状の物理精度収束は未完 |
| 弧端・退化の分類 | offset_degeneracies.py、test_offset_degeneracies.pyの追加9検査とdiagnose-offsets CLI。共有パラメータ、円の外接/内接/潰れ、直線の接触/重複を有限範囲と区別 | 特殊ケースを部分受入。[診断仕様](OFFSET_DEGENERACIES.md)。構築版5/6の実探索区間から別保存/CLI/GUIへ接続し、追加5検査/Chrome11操作PASS。一般の重解/全弧端と退化候補構築は未完 |
| 同一支持円の有限弧・同じ楕円/双曲線の自己接点 | coincident_circle_arcs/general_coincident_circle_arcs/same_conic_offset_intersections、追加21unit、独立20496条件、標準1456/主41unit、実Chrome292チェック/182取得。[受入詳細](G03_FINITE_OFFSETS_CHECKPOINT.md) | 全候補周期と反射接点の所属/重複が証明できた専用範囲を受入。異なる支持円錐曲線の一般重解・全弧端、新しい退化フィレット構築、物理ピーク収束は残る |
| 旧曲線指定との対応 | COMPATIBILITY_BASELINE.md、LEGACY_INPUT.md。現在は限定AF部分集合のみ | **未完**。旧仕様・対象版・変数別の確認と入力/数値出力比較が必要。native表現で代替して完了にはしない |
| 物理的な表面ピークの収束 | 曲線場の連続離散極値・元曲線角診断は実装済み | **未完**。離散場の囲い込み/小残差を物理ピーク収束へ読み替えない。N03の独立細分証拠も必要 |

ソース名はsrc/superfish_ng/、テスト名はtests/に対する表記。
版6GUIはout/gui-line-conic-fillet-browser-20260908/report.jsonのChrome8操作で版6統合時に確認した。
今回の構築診断はout/gui-construction-diagnosis-browser-20260908/report.jsonのChrome11操作で確認。
既存版1〜5の記録と再読込も確認した。標準回帰の最新件数は
[実装状況](IMPLEMENTATION_STATUS.md)と[引継ぎ](CODEX_HANDOFF.md)に保持する。

版5/6で根箱からの有限接点と有向フィレットを製品操作へ接続。特殊ケースの診断を追加した。診断の構築保存/CLI/GUI接続まで実施し、同一支持曲線の専用分類を追加受入し、異なる支持曲線の一般弧端/重解分類は残る。
単一の初期値から収束した根を全候補列挙と扱わず、予算不足・接触/重根・潰れを残す。
部分受入を全フィレット・旧入力・物理収束の証拠へ拡張しない。G03全体と全計画の完了判定は保留する。
