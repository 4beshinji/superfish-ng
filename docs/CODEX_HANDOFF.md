# ローカルCodexへの引継ぎ

## G03の弦Contour変換 — 2026-09-08

CurvedContour.linearize→ChordApproximationを追加。タグ/元曲線対応・端点調整・解析面積差を保持。
端点調整を誤差予算から差引き、全体分割数上限とContour再検証・向き検査を行う。
半楕円の面積/独立楕円体体積収束、タグと元曲線不変を検証。
標準212件中210合格・2 skip、validation-g03-chord-contour-20260908 PASS。
次はCaseへ元曲線/弦誤差を保持する契約と保存、一般の解析体積。曲線FEM等は未完。
G03と全互換目標は継続。

## G03の単一曲線閉輪郭 — 2026-09-08

curved_contour.CurvedContourを追加。軸鎖/タグ/範囲/全辺対/正面積を検査し、
検査用二分で軸+半楕円の2辺形状も扱う。位置許容差は軸長1e-10以下、元形状は修復しない。
半楕円解析面積/寸法変換・分割軸混在タグ・交差/不正タグ/隙間を検証。
標準210件中208合格・2 skip、validation-g03-closed-curves-20260908 PASS。
次は弦近似Contour変換と幾何誤差/体積、Case元曲線保持。曲線FEM/旧入力対応も未完。
G03・全互換目標は継続。

## G03の隣接曲線検査 — 2026-09-08

directional_derivative_boundsとcertify_adjacent_curvesを追加。共有端点近傍は共通方向の
厳密な投影単調性、残り区間対は通常の離隔検査。許容差内の逆順重なりをUNVERIFIEDで拒否。
中心差分・線分/楕円・直角・逆向き・探索上限を検証。標準207件中205合格・2 skip、
validation-g03-adjacency-20260908 PASS。次は閉輪郭/軸連続性/辺タグ/全辺対/モーメント統合。
Case/GUI/曲線FEMは未接続、G03と全互換目標は継続。

## G03の区間包絡と離隔 — 2026-09-08

curve_bounds.pyに線分/楕円/双曲線の座標極値と余裕付き包絡箱、区間対細分の離隔検査を追加。
距離不足FAILと探索上限UNVERIFIEDを分離。共有端点を持つ隣接辺にはまだ適用しない。
解析極値・軸横切り・既知距離・交差/接触・同心円弧の検証が合格。
標準205件中203合格・2 skip、validation-g03-bounds-20260908 PASS。
次は閉輪郭への統合、共有端点近傍と非隣接辺の検査、軸/タグ契約。
Case/GUI/曲線FEM・旧入力対応は未完、全互換目標は継続。

## G03の線分・接線接続検査 — 2026-09-08

LineSegmentとcheck_curve_joinを追加。端点SI許容差と有向接線角を別判定し、形状を修復しない。
G1とC1/曲率連続を区別。線分↔楕円↔双曲線接線、逆向き/隙間/角/元形状不変を検証。
標準202件中200合格・2 skip、validation-g03-joins-20260908 PASS。
次は曲線区間の位置/誤差包絡、閉輪郭の交差/軸/隙間検査。
Case/GUI/曲線FEMと旧入力対応は未完、G03と全互換目標は継続。

## G03の双曲線弧コア — 2026-09-08

conics.HyperbolaArcに有限区間/枝±1、点/接線/曲率/最小半径/面積寄与/弦近似を追加。
両枝の陰関数・勾配直交・頂点半径・反転/面積・寸法と誤差を検証。
標準199件中197合格・2 skip、validation-g03-hyperbola-20260908 PASS。
次は線分/楕円/双曲線の接線接続契約と、曲線境界の交差/軸/隙間検査へ進む。
旧入力対応、Case/GUI/曲線FEMは未接続。G03と全互換目標は未完。

## G03の楕円弧コア — 2026-09-08

CONIC_GEOMETRY.mdで幾何/曲線FEMを分けた仕様段階を定義。
conics.EllipseArcに回転楕円の点/接線/曲率/最小半径/面積寄与/誤差上限付き弦近似を実装。
陰関数・直交・円極限・回転/反転・四分面積・寸法変換で独立検証。
標準196件中194合格・2 skip、validation-g03-ellipse-core-20260908 PASS。既存mode/hash不変。
次は双曲線プリミティブと接線接続契約、曲線の交差/軸/隙間検査へ進む。
Case/GUI/曲線FEM未接続、G03および全互換目標は未完。

## G02受入完了 — 2026-09-08

GENERAL_MESH.md末尾で全要件/実装/証拠を照合しG02.S/I/Vを受入。
実Chrome初回で結果表示のprofile前提を検出し、長さ取得/掃引/バンドを修正。
再検証5操作PASS、外部通信0、サーバー停止済み。細分Studyが最大辺長を変更しない問題も修正。
標準192件中190合格・2 skip、validation-g02-gui-fixed-20260908 PASS、旧mode/hash不変。
次はG03.S（円/楕円/確認済み双曲線、接線・曲率・丸め、幾何と曲線FEMの分離）へ進む。
C00未確認と残り親課題・全互換目標は継続。

## G02の自動solve/CLIとGUI欄 — 2026-09-08

make_meshをCase.contour_meshへ接続、未指定時は明示拒否を維持。自動/明示mesh一致、
保存Case再計算係数一致を検証。実CLIの合成folded例も全RF/hash/係数完全一致。
GUIに4設定欄とSI保持を実装し、contourでnr/nz/triangulationを無効化。
標準191件中189合格・2 skip、validation-g02-auto-20260908 PASS、JS構文PASS。
次は実Chromeでcontour読込→設定編集→solve→出力/再読込を検証し、G02全要件を照合。
examples/contour_folded.jsonは粗い操作例。全互換目標とG02は継続。

## G02の方式判断とCase制御契約 — 2026-09-08

ADR-017で測定に基づき自前品質判定方式を選択。ContourMeshControlsとv3
mesh.contour_meshへ最大長/最小角/要素・反復上限を追加しstrict解析・保存往復を検証。
標準191件中189合格・2 skip、validation-g02-controls-20260908 PASS。
次はmake_meshが設定から自動生成する接続とCLI/保存再実行、GUIの欄/読込保持/実操作。
現時点make_meshのcontourはまだ拒否する。新設定をGUIcollectはまだ保持しないので要対応。
G02全体・全互換目標は未完。

## G02の非円筒独立照合 — 2026-09-08

compare_contour_ngsolve.pyを追加。円錐台はPASS、折返しの初回周波数未収束FAILを残し、
.0015/.00075/.000375の双方追加細分でPASS。CONTOUR_RF_COMPARISON.mdに閾値/数値/費用を記録。
最終差f1.34e-5/RQ1.56e-5/G1.54e-5、内部H/EもPASS。最細NG36万DOF/84秒。
標準189件中187合格・2 skip、参照専用7件PASS。全ジョブ完了。
検証環境/tmp/superfish-g02-reference（隔離、NGSolve6.2.2606/NumPy2.5.3/SciPy1.18.1）。
次は方式ADRと製品のサイズ/品質/停止上限のCase契約、保存/CLI/GUI接続へ進む。
一般輪郭make_meshはまだ明示拒否。表面角ピークは未受入、G02・全互換目標は継続。

## G02の点追加と品質判定 — 2026-09-08

quality_contour_meshで悪い要素の最長辺へ境界を含む点追加、組替え/移動を反復。
目標最小角を全要素で達成したときだけ返し、反復/要素上限は明示失敗する。
測定mesh-g02-quality-20260908: 幅0.05は831要素12.61度、0.01は2336要素10.03度。
幅1e-5は4000要素上限でFAIL。標準188件中186合格・2 skip、validation-g02-quality-20260908 PASS。
次は独立非円筒RF参照との収束、方式/資源判断、Caseサイズ品質契約と製品経路を進める。
G02全体および全互換目標は未完。make_meshのcontour公開はまだ拒否のまま。

## G02の内部頂点移動 — 2026-09-08

smooth_contour_interiorで境界を固定し、関係要素の最小qを改善する内部点移動を追加。
正の向き・サイズ・タグ・独立モーメント/再現性を検証。標準187件中185合格・2 skip、
validation-g02-smoothing-20260908 PASS。幅0.5で最小角14.0→15.6度、幅1e-5は
0.000286→0.000368度に留まる。次は境界点追加を含む配置/必要要素数/品質拒否条件を評価。
G02の製品契約/自動solve/独立非円筒RFも未完。全互換目標は継続中。

## G02の内部辺組替え — 2026-09-08

improve_contour_anglesで境界/頂点を保ち2要素の最小角が改善する内部対角辺だけ交換。
最大長/局所サイズ保持、幾何モーメント、再現性/固定点を検証。標準186件中184合格・
2 skip、validation-g02-flips-20260908 PASS。測定mesh-g02-flips-20260908では品質中央値は
改善したが狭い経路の最小角は不変。次は頂点配置/追加方式と必要要素数を評価する。
Caseサイズ契約/自動solve/独立非円筒RF受入も残り、G02・全互換目標は未完。

## G02の適合細分化と品質測定 — 2026-09-08

refine_contour内部APIで共有中点/最長辺閉包/タグ継承、全域・境界・角サイズと停止上限を
実装。独立面積/体積・局所タグ長とサイズ達成が合格。標準185件中183合格・2 skip、
validation-g02-refinement-20260908 PASS。measure_contour_mesh.pyの測定で狭い経路の
最小角は細分しても改善しない（幅1e-5で0.000286度）。次は品質改善方式と必要要素数・
失敗条件/依存判断を測定。Case全域サイズ契約/自動solve/独立非円筒RF参照も残る。
G02は未受入、全互換目標は継続。

## G02の初期三角形分割 — 2026-09-08

GENERAL_MESH.mdで段階と受入条件を定義。contour_mesh.triangulate_contourは
全頂点/辺タグを保つ初期分割を実装し、独立矩形/円錐モーメント・狭い経路を検証。
標準182件中180合格・2 skip、validation-g02-initial-20260908 PASS。
make_meshの一般輪郭はまだ明示拒否。次はタグ継承を保つ細分化、全域/局所サイズ契約、
品質改善と停止制限を実装・測定する。G02.S進行中/I部分/V未受入、全互換目標は継続。

## G01受入完了 — 2026-09-08

GENERAL_CONTOUR.md末尾で要件/実装/証拠を照合しG01.S/I/Vを受入。
一般輪郭と混在タグのGUI実ChromeもPASS。最終標準178件中176合格・2 skip。
能力表はcontour対応と外部mesh必須を別表示。次はG02.Sの一般輪郭自動メッシュ方式・
品質検査・依存採用判断を仕様化し、実装/検証へ進める。全互換目標は継続中。

## G01の後処理点検 — 2026-09-08

一般輪郭のradial probe/plotは領域外の隙間をNaNで表現。CSVにinsideと
metadata規約を追加し、矩形分割の既知ギャップで検証。円筒参照/バンド/反復組立は
適用外を明示拒否。標準178件中176合格・2 skip、validate PASS。
次は混在タグGUIの実ブラウザ確認とG01全要件の受入照合。自動meshはG02。

## G01の局所端面タグ — 2026-09-08

混在端面をCaseの導出mixed要約で保持し、外部meshは辺タグを正として検証。
P2局所拘束と全面PEC/部分磁気/全面磁気の変分周波数順序、鏡映拒否が合格。
178 tests中176合格・2 skip、標準validate PASS。
GUI混在要約を実装・構文確認済み。次は混在GUIの実ブラウザ確認と、G01全経路の
未対応profile前提（解析比較/半径プローブ/組立等）を点検し、適切に移行/拒否して受入する。

## G01の実ブラウザ往復 — 2026-09-08

一般輪郭のファイル読込/8頂点表示/Case出力/再読込が実ChromeでPASS。
端面欄の無視される編集を修正し、読込辺タグの無効化表示にした。
証拠gui-g01-browser-final-20260908/report.json、標準validate PASS。サーバー停止済み。
次は局所端面タグをCaseで制限している箇所を整理し、G01仕様/証拠を最終照合する。
G01全体は未受入。

## G01の一般輪郭プレビュー接続 — 2026-09-08

gui.preview_documentを追加し、閉輪郭/タグ/面積/体積を返す。web/app.jsは
読込contourを保持し閉多角形として描画。ファイルによる形状編集を画面で説明する。
API往復・解析モーメントとJS構文は合格。次は実Chromeでcontourファイル読込・
プレビュー・Project/Case出力・再読込を検証する。局所タグ制限整理も残る。G01未完。

## G01のCase/FEM鏡映 — 2026-09-08

reflect_solutionでContour.reflectedを全Caseへ渡し、P2外部meshの
全領域再計算とf/RQ/損失を比較した。z折返しの両端×電気/磁気4条件PASS。
標準176件中174合格・2 skip、validate PASS。
次はgui.pyの/api/preview付近のlinearize_profile前提とweb/app.jsの形状保持を
一般輪郭へ移行する。局所端面タグの暫定制限も整理し、G01受入へ進む。

## G01の外部メッシュ接続 — 2026-09-08

mesh_from_dictを一般輪郭へ対応。辺単位タグ/投影区間の完全被覆、面積/接続/軸を検査。
矩形分割のz折返し外部meshでP2 solve→保存→読込が合格。
176 tests中174合格・2 skip、標準validate PASS。
次はプレビューと鏡映Case/FEMをprofile前提から移行し、局所端面タグの制限も整理する。
自動生成はG02まで未対応。G01全体は未受入。

## G01のCase v3連携 — 2026-09-08

Case((),contour=...)とv3 contour geometryを追加。profileは偽造せず空、
length/areaは輪郭から取得。175 tests中173合格・2 skip、標準validate PASS。
make_meshはG02、mesh_from_dictはG01検証移行待ちとして明示拒否中。
次は外部meshの境界検証・プレビュー・鏡映Case/保存を移行する。
同端面内の混在タグはCaseで暫定拒否。局所タグ契約も移行時に解決する。G01未完。

## G01の変換・鏡映 — 2026-09-08

Contour.from_profileとreflectedを実装。独立円錐台体積・z折返し鏡映の
面積/体積2倍を検証。標準174件中172合格・2 skip、validate PASS。
次はCase v3のcontour geometryを追加し、profile前提の長さ/境界/プレビュー/保存を
移行する。一般輪郭の外部mesh検証もG01対象。自動メッシュはG02まで未対応と明示する。

## G01の一般輪郭コア — 2026-09-08

GENERAL_CONTOUR.mdへ仕様を追加。contour.Contourでz折返し多角形の
厳密検証・向き/始点正規化・面積/体積を実装。矩形分割・円錐・寸法変換で独立検証。
172 tests中170合格・2 skip、標準validate PASS。
次は既存profile変換・鏡映・Case v3統合・外部mesh検証を進める。
G02の一般輪郭メッシュ生成は別段階で、現行R(z)生成へ黙って通さない。G01未完。

## N02受入完了 — 2026-09-08

HIGH_ORDER_FIELDS.md末尾で仕様・実装・証拠を照合しN02.S/I/Vを受入。
能力表・現在仕様をP1/P2へ更新。標準169件中167合格・2 skip、総合13チェックPASS。
次はG01.S（z折返し可能な単一外周・軸閉領域・厳密な不正輪郭拒否）から実装/検証へ進む。
G02の任意輪郭メッシュは別依存段階。C00の未確認行とC03/C04、他の全親課題は継続対象。

## N02の総合数値検証 — 2026-09-08

validate_quadratic_fields.pyで独立J0/J1/cos/sin場・ピーク・RF・同DOF比較を検証。
13チェックPASS、証拠quadratic-fields-n02-final-20260908/fields.json。
Job取込再実行の係数/RF一致と寸法スケーリングも追加。標準169 tests中167合格・2 skip。
次は能力表・PHYSICS/README/進捗のP1限定記述を現実装へ整え、N02.Sの全移行箇所・
受入条件と証拠を照合してN02を受入する。全32項目・33親課題の目標は引き続き未完。

## N02のGUI次数選択 — 2026-09-08

P1/P2選択、v3/model生成、Project読込往復を接続。実Chromeの4操作と
標準validate PASS。証拠はgui-n02-order-browser-final-20260908/report.json。
今回のGUIサーバー停止済み。次は能力表・現在仕様の記述を更新し、
Bessel全場/ピーク/誤差対DOF/Job再実行を総合検証してN02全体を受入する。

## N02のCase/CLI次数 — 2026-09-08

v3 solver.element_orderで1/2をstrict受理。solveが次数を選択し、Project・保存・
再読込・再実行まで保持。旧Case研究P2保存は次数2をCase/鏡映元へ明示する。
167 tests中165合格・2 skip、標準validate PASS、P1 mode/hashは不変。
次はGUIの次数選択と入出力保持、能力表/文書を更新し、総合Bessel場・ピーク・
誤差対DOF/半全・Job再実行を検証する。N02全体は未完。

## N02のバンド・細分比較 — 2026-09-08

analyze_bandはP2セル中心と軸停留点、compare_refinementは高次Hと
P1/P2差の正確な軸積分を使用する。既定read_solutionでP2を読める。
165 tests中163合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はCase/Project/CLI/GUIへ次数を保持して再実行を可能にする。
Job取込は保存P2を保持できるが、Case次数がまだ無いため再実行の次数保持は未完。
Bessel場/ピーク/誤差対DOFの総合証拠を整え、N02全体を受入する。

## N02の保存P2解析/probe — 2026-09-08

export_radial_probeとcompare_pillboxが高次reader/samplerを使用する。
円筒解析の軸L2はP2軸辺の8点Gauss評価へ対応。3モード同定・全ゲート、
元解とのCSV場一致を検証。164 tests中162合格・2 skip、標準validate PASS。
次はanalyze_bandとstudiesの高次場/軸評価を移行し、既定読込の暫定拒否を撤去。
Case/CLI次数指定と総合Bessel/ピーク/DOF比較も残る。

## N02の保存P2描画 — 2026-09-08

plot_modeを検証済みreader/display_fields/高次samplerへ移行。保存P2から
電場・磁場・軸・radialを描画し、元解とのprobe一致と未完了拒否を検証。
163 tests中161合格・2 skip、標準validate PASS。PNG目視証拠は
out/p2-plot-20260908/mode2.png。次はsaved解析/probe・studiesへ高次場を渡し、
read_solutionの既定拒否を撤去する。Case/CLI次数と総合N02検証も残る。

## N02のP2保存・明示読込 — 2026-09-08

save_runでP2全係数/4空間配列/field_space宣言を保存。read_solutionの
allow_quadratic=Trueで再構成空間との一致を検証して読める。
162 tests中160合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はsavedのprobe/比較/バンド、visualize、studiesへ空間を渡す。移行完了後に
読込の暫定制限とplot_modeの拒否を撤去する。Case/CLI次数指定も残る。N02未完。

## N02の表示用分割・VTK — 2026-09-08

display.pyへP2の4分割表示データを追加し、write_vtkに接続。
二次多項式の場・面積・VTK値を検証。161 tests中159合格・2 skip、標準validate PASS。
P1のRF全量/hash/VTKバイト列は不変。次はsave_run/read_solutionへ次数・全係数・
接続情報を保持して移行し、plot_modeと追跡へつなぐ。N02全体は未完。

## N02のP2鏡映 — 2026-09-08

reflect_solutionを全中点の偶奇写像へ拡張。両端×電気/磁気対称について
独立全領域solveと周波数/RQ/損失の一致、場の偶奇、U/損失2倍を確認。
159 tests中157合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はP2保存/再読込/表示/追跡とBessel場・ピーク/誤差対DOF証拠を進める。
HIGH_ORDER_FIELDS.mdに記録。N02全体の受入とCase/CLI次数公開は未完。

## N02の表面積分とRF量 — 2026-09-08

quadratic_rf.surface_integrals_p2を実装し、rf.quantities/cell_fieldsへP2を接続。
既知多項式の損失/内部極値、3モードのRQ/G収束・Uスケーリングを検証。
158 tests中156合格・2 skip、標準validate PASS。P1 mode全量とhashは不変。
次はBessel全場/ピーク/誤差対DOFの証拠とP2保存・再読込・鏡映/描画/追跡統合。
HIGH_ORDER_FIELDS.mdを参照。Case/CLIのP2指定はまだ未公開でN02は未完。

## N02の軸電圧積分 — 2026-09-08

quadratic_rf.pyへ二次軸場の複素電圧/絶対値積分とP2解アダプタを追加。
低beta・部分区間・符号反転を独立積分で検査。155 tests中153合格・2 skip、
標準validate PASS。HIGH_ORDER_FIELDS.mdに式と証拠を記録した。
次はPEC表面損失/極値、quantities/cell_fields統合、その後保存/描画/鏡映/追跡。
N02全体と継続目標は未完。

## N02の場評価を開始 — 2026-09-08

HIGH_ORDER_FIELDS.mdにN02仕様と全移行箇所を記録。FieldSamplerは明示したP2空間の
6係数を保持し、from_solutionで次数整合を検証する。独立多項式/軸極限テスト合格。
152 tests中150合格・2 skip、標準validate PASS、P1の周波数/RFとhashは不変。
次は二次軸電圧の安定積分・PEC辺積分/極値。その後RF/保存/表示/鏡映/追跡を統合する。
N02は実装途中であり、全体の受入は未完。

## N01のP2固有値コア — 2026-09-08

N01.S/I/Vを受入。QUADRATIC_ELEMENTS.mdに独立積分・収束・再現手順を記録。
研究用high_order.solve_p2のみ公開し、P1用の場/RF/保存/鏡映はP2解を明示拒否する。
150 tests中148合格・2 skip、標準validate PASS。既存の円筒/成形セルのmode全量は直前と一致。
次はN02.Sで高次係数を保つ場評価・RF積分・保存・描画・鏡映・追跡を設計し、実装/検証する。
32項目・33親課題全体の目標は継続中。以下の古い開始点は履歴として読む。

## R01の加速量規約 — 2026-09-08

R01.S/I/Vのnative範囲を完了。ACCELERATING_CONVENTIONS.mdに仕様・再現・失敗履歴を記録。
v3 rfのactive_length_m、voltage_interval_m、phase_origin_mを追加し、旧既定値/hashを保持。
解析比較、鏡映写像、CLI/GUI/保存を更新。143 tests中141合格・2 skip、標準validate PASS。
最終GUIはout/gui-r01-browser-accepted-20260908、数値はout/validation-r01-final-20260908。
初回の区間外掃引拒否と撮影待ちFAILを保持する。旧入力の任意ZCTR等はまだ受け入れない。
次はN01.SのP2要素/解契約→N01.I/V、N02の場/RF/保存・表示への移行を進める。
N02受入まで高次RFを製品公開しない。C00の未確認行とC03/C04も継続対象。

## O01の保存完了管理 — 2026-09-08

O01.S/I/Vのローカル契約を完了。SAVE_COMPLETION.mdに仕様と受入を記録した。
save_runは出力先を排他予約し、内部一時領域で全ファイルを作り、非置換hard linkで
完了マーカーを最後に公開する。read_solutionは全必須出力のhashを検査し、旧形式も読む。
Job取込の外部meshコピー漏れを修正し、新しい直接保存の完了証拠を区別して保持する。
137 tests中135合格・2 skip、out/validation-o01-accepted-20260908がPASS。
R01の加速量規約とN01/N02、C00調査、C03/C04は未完。次はR01.Sから進める。

## C02限定AF読込の受入 — 2026-09-08

LEGACY_INPUT.mdのC02初期部分集合を仕様・実装・検証まで完了。
import-afはnr/nz/modes/導電率/正規化を明示必須とし、DX/FREQ等の無適用を診断に記録する。
単一REG・全PEC・軸接続真空TM・直線/段差/NT4/5短円弧のみ受理。その他は位置付き拒否。
128 unittest中126合格・2 skip、out/validation-c02-final-20260908がPASS。
保存AF2形状からの新規NG4計算と既存SFO照合はout/c02-import-acceptance-20260908。
新規旧計算・場全体/表面ピークの受入ではない。C00/C03/C04と汎用旧入力は未完。
次はR01の加速量規約、またはO01の直接保存完了管理を仕様化して実装する。

## C01共通契約の受入 — 2026-09-07

C01.S/I/V完了。仕様・実行証拠・再現はMODEL_CONTRACT.md。
v3 modelとcapabilities/migrate-caseを実装し、v1/v2のhashと既存解を保持した。
Project/Study/GUI/鏡映/外部meshの保存でmodelを失わず、追加物理は計算前に拒否する。
122 unittest中120合格・参照環境専用2 skip、標準validateとChrome 8操作検査PASS。
最終証拠はout/validation-c01-final-20260907、out/gui-c01-browser-final-20260907。
次はC02.SでDXのNG指定への写像、FREQ等の探索指定、未指定導電率/正規化の扱いを
明記し、確認済みAF部分集合のstrict読込と変換記録を実装する。C00調査は未完了のまま継続。

## 互換開発goal開始 — 2026-09-07

ユーザーが32対応項目・33親課題の完遂をgoalに指定。作業checkoutは
`/home/sin/code/agent/reserch/superfish-ng`。C00の最新記録はCOMPATIBILITY_BASELINE.md。
全32項目の受入軸、限定TM辞書と未確認事項、保存出力のAutomesh/Fish/SFO/SF7版、
参照ファイルhashを記録した。C00.Vは未完了。次はC01.Sの共通契約とC02.Sの
メッシュ/探索/未指定RF設定の変換契約を具体化し、C00の追加ツール調査も継続する。
開始時114 unittest中112合格・参照環境専用2 skip。今回の旧計算再実行はなし。
以下の計画整備のみを対象とした指示より本節を優先する。

## 現在の入口 — 2026-09-07 計画整備

最新指示は「実態に合わせて計画更新→互換対応表→作業分割」。このターンは計画を整備する。
計画整備v0を完了。[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)のK01〜K32と
[COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md)の.S/.I/.Vを次の作業単位とする。
次はC00の版・入力集合の確定→C01.Sの共通契約。高次要素へ直ちに飛ばない。
表のH/Uは対象版未確認、Xは互換必須集合外。仕様調査未完を互換完成と混同しない。
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)と[BACKLOG.md](BACKLOG.md)を正本とし、
以下の履歴内の「次は…」やseed開始プロンプトより優先する。
製品基準1f5cd84で114テスト中112合格・2 skipを再確認。物理範囲や製品コードの変更はない。
P1-03は平坦z端で完了、P2-04はGUI範囲で完了。一般追跡・tune・直接保存の原子的完了は残る。

以下は日付付きの実施履歴。テスト件数・実行環境は各時点の値を保持する。

## 互換性拡張の再開 — 2026-09-07

ユーザーは可能な範囲で互換拡張を進め、区切りごとのローカルコミットを指示した。
P0-01のNGSolve独立照合を完了。仕様と再現はINDEPENDENT_COMPARISON.md。
通常環境の基準101テストは合格。検証専用venvは
`/tmp/superfish-ng-independent-20260907`。本体の依存・FEM・RFは変更していない。
次はP0-02のタグ付き非構造メッシュ。旧入力互換や物理範囲拡張の完了ではない。

同日P0-02/P0-03も完了。`solve case.json --mesh mesh.json --out ...` と
`solve(case, mesh_data=...)` を追加。仕様・受入はMESH_INPUT.md。
114件中112件合格・参照環境専用2件skip、標準数値検証PASS、既存周波数差ゼロ。
次の数値拡張候補はP1-01。メッシュの読込で対応物理範囲は増えない。

## 汎用GUI・共通入出力の計画 — 2026-09-06

ユーザー依頼に基づき [GUI_IO_PLAN.md](GUI_IO_PLAN.md) を作成した。
例題専用の処理を作らず、対応物理範囲の汎用操作を提供し、KEK対象操作と例題外の
合成ケースで受け入れる。追加機能・抽象化は全体品質への寄与で判断する。
追加指示でG0〜G5の受入完了を `/goal` に設定した。ADR-009/010により
Project・JobManager・保存結果読込・Study・ローカルGUIを共通化した。
新規Web/Qt依存なし。形状編集、旧結果取込、掃引/収束/比較/分散を実装済み。
32数値受入、101 unittest、別環境へ展開したwheelのGUI計算/描画がPASS。
G0〜G5の技術的受入を完了。実行証拠・対象外・主観評価の未実施はGUI_ACCEPTANCE.md、
操作はGUI_GUIDE.mdを参照。
`python -m superfish_ng gui --workspace out/gui-workspace` で起動する。
既存の半端部バンド同定を任意形状へ適用しない。一般mode tracking・tuneは本計画の対象外。

## 境界・局所メッシュ改善 — 2026-09-06

任意のv2 mesh設定で境界辺と角周辺の内部辺を実長制御する。既定は従来経路。
設定仕様はINPUT_OUTPUT.md、検証数値と制約はPHYSICAL_MESH_REFINEMENT.md。
最終9計算は `out/physical-mesh-final-20260906/`。1 mm固定点変化26.14%→2.21%、
PEC接線比7.95%→1.52%。節点約3.25倍であり同コスト優位の証明ではない。
円弧には境界サイズのみ対応。P1電場復元と鋭角特異性は変わらない。

## 角部診断の追加 — 2026-09-06

ユーザーの質問を受け、P1-04の切り分け評価を実施。
[SURFACE_FIELD_DIAGNOSTICS.md](SURFACE_FIELD_DIAGNOSTICS.md)に新規計算と解釈を記録する。
鋭角のEpkは細分で上昇するため、過去のNG–Wine差14.8%を有限厳密値の誤差と解釈しない。
実装本体は変更していない。現checkoutには過去out/がなく、ユーザー許可でWine比較環境も新設した。
NG25計算（元の19＋真空側固定点6）とWine鋭角/接線円弧各4段階を完了。
最終参照は `out/surface-wine-arcs-20260906/report.json`、図と集約値は
`out/surface-wine-report-final-20260906/`。鋭角の生結果は検査して再利用した。
Wine最細の鋭角ピーク変化17.48%、丸み対照ピーク変化2.81%を未収束として残す。
丸み対照のNG–Wine差は1.21%。今回の診断をP1-04全体の完了やEpk精度保証と呼ばない。
78テストと `out/validation-surface-final-20260906/` の既存数値検証は合格。
Wineランタイムは `/tmp/superfish-wine-runtime/`。一時領域の掃除後は再作成が必要。

## 現在の優先目標（2026-09-05更新）

ユーザー指定の [セミナー4資料の例題計算・可視化](MILESTONE_SEMINAR.md) は完了。
最終結果は `out/seminar-suite-final-20260905/index.html`、受入監査は [MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)。
9数値ジョブ・69テスト・7ページ検査がPASS。全NGは新規計算、Wineは入力・hashを検査して再利用した。
最終suite.jsonはPASSかつsource_changed_during_run=false。継続待ちの計算プロセスはない。
以下の個別試行・失敗も履歴として保持する。次の機能拡張はユーザーの次の指示で選ぶ。
Wine版SUPERFISHとの3形状の基本モード照合は完了し、[比較結果](SUPERFISH_COMPARISON.md) を保存した。
S1の全領域TM010/TM011・長さ掃引・図・CSV・HTMLとWine/SF7照合は実装済み（[記録](SEMINAR_PILLBOX.md)）。
S1の半領域の電気／磁気対称境界・全空洞鏡映も完了。`seminar_symmetry.py` で再現可能。
段差・円弧、4/7モード同定と分散曲線も実装済み。[記録](SEMINAR_MULTICELL.md)を参照。
flat4はNG nr=128/256/512とWine dx=0.05/0.025/0.0125/0.01で全照合・収束PASS。
`out/seminar-flat-ready-20260905` とheadless検査 `out/gallery-test-flat-ready-20260905` が最終結果。
rounded4はNG・形状近似・Wine3段階の全検査合格（`out/seminar-rounded4-wine-comparison-20260905`）。
rounded7は任意のcrossed分割を追加し、nr=64/128/256で全量PASS。
`out/seminar-rounded7-crossed-native-20260905` と `out/seminar-rounded7-crossed-geometry-20260905` を参照。
円弧半領域の鏡映にも対応したが、対称反射だけのR/Q改善試験は不成功。失敗試験も保存済み。
rounded7のWine3段階は `out/seminar-rounded-wine-20260905/rounded7` で完了。
full-end切断面を実装した `scripts/seminar_end_cells.py` も追加。初回検査はflat/halfのR/Qだけ1.1521%でFAIL。
追加nr=384で変化0.32373%を確認し、`out/seminar-end-cells-ready-20260905` の最終レポートはPASS。
`out/gallery-test-end-cells-ready-20260905` で全8選択肢・51リンク/画像のheadless検査も合格した。
Pillbox/rounded4/7のHTMLはheadless Chromeの実キー入力で検証済み。Orcaの既存デスクトップ操作は行っていない。
S6の `scripts/seminar_suite.py` と入口HTML生成を実装し、`out/seminar-suite-20260905` の全NG計算・全7画面検査は終了。
全体FAILの原因は7セルπモードのWine側R/Q細分1.98217%とTTF。NG–Wine差は全モード合格。
RAM設定で追加DX=0.01/0.011 cmはSFO生成前に失敗。ローカルSF.INIのStoreTempDataInRAM=Noを使う
`out/seminar-rounded7-wine-extra-20260905/disk-dx0.01/mode7` が正常終了。既設SF.INIは変更していない。
πの追加R/Q細分変化0.658403%、NG–Wine差0.757236%で合格。元の未達履歴は消さない。
モード別追加細分の検証を実装し、`out/seminar-suite-final-20260905` で全NGを再び新規計算してPASS。
参照は既存Wine生出力を検査して再利用し、必要なrounded7出力は最大14400秒の読取専用待ちを明示した。
開始時のsource/tests/scripts/examples hashと終了時の一致を確認した。今後も一括実行中にはソースを編集しない。
最終suite.json、全子レポート、参照ファイル、画面とリンク先のhashも再監査した。
追加参照を含む比較はfinal_legacy_modesを読む。legacy[-1]は追加前の履歴であり、πの旧FAILが意図的に残る。
操作手順と判定仕様は [SEMINAR_SUITE.md](SEMINAR_SUITE.md)。
以下の開始プロンプトはseed時点の記録で、次課題P0-01の優先順はこの更新で置き換える。

## 開始プロンプト

以下をそのままCodexへ渡せる。

```text
このSuperfish-NGリポジトリを継続開発せよ。
AGENTS.md、README.md、docs/PHYSICS.md、docs/PROVENANCE.mdを最初に読み、
ローカルでテストとscripts/validate.pyを実行して初期状態を確認すること。
旧SUPERFISHのソースやバイナリは参照・使用せず、公開された数学と
明示的なライセンスを持つ現代のOSSだけを使用する。

次の目標はdocs/BACKLOG.mdのP0-01「外部ソルバでの独立照合」である。
同じ幾何形状・境界・phasor・単位・R/Q規約を固定し、NGSolve等で
独立に計算して比較する。参照ソルバを導入できなければ、比較済みとは
主張せず、実行可能な比較用入力と未実行の理由を残すこと。
その後P0-02の境界タグ付き非構造メッシュ対応へ進む。

科学的な回帰を起こさず、小さなコミットで進めること。
周波数だけを解析値に合わせてRF量の精度を保証したことにしない。
変更内容、検証結果、未解決事項、次に実行するコマンドを最後に報告せよ。
```

## 現在の動作経路

`Case.load → make_mesh → assemble → solve → quantities → save_run`。
式と積分は `src/superfish_ng/fem.py` と `rf.py`、独立解析解は `analytic.py`。
テストは `unittest` 69件。seedの主要数値は `benchmarks/validation/`、最新照合は `docs/SEMINAR_PILLBOX.md` と `docs/SEMINAR_MULTICELL.md`。
出力は別の新規ディレクトリへ作る。既存ベンチマークを直接上書きして初期値を失わないこと。

## 直近の注意点

- P1のuはr³重みのエネルギーでは良好でも、軸上Ezの点値収束はより遅い。
- 自由度は節点u=Hφ/r。VTKに出すHφはrを掛ける。軸上uを0にしない。
- 電場のP1微分を節点平均で平滑化すると見た目は改善してもピーク値が偏る。未評価の平滑化を設計指標に混ぜない。
- 無限に鋭い角を持つ形状ではEpkのメッシュ独立値が存在しない可能性がある。丸め半径を仕様にする。
- 既定のactive lengthは全長。多セルやビームパイプ追加時に自動流用しない。
- seedのQR/直交化はeigshに任せ、物理的な勾配nullspaceを除去したことにはしない。現在のTM縮約に3D機能を足す際に再設計する。
- `save_run`は出力ディレクトリを新規作成するが、ディスク書込み全体のトランザクション化は未実装。途中失敗したディレクトリは完了扱いしない。

## 環境の再現

通常は `pip install -e .`。納品時のPython 3.12系に揃える場合は
`pip install -r requirements-reproduce.txt` の後 `pip install -e . --no-deps`。
このファイルはプラットフォームごとの依存ハッシュを固定したlockfileではない。
OS・BLAS・CPUや縮退モードの基底は変わり得る。期待値は許容誤差で比較する。

CIはLinux/Python 3.10と3.12を対象とする定義を同梱したが、納品時の実行実績はローカルPython 3.12のみ。
依存環境を整えたユーザーPCでのテスト結果を次の記録として保存する。

## 完了報告の基準

新しいバックエンドは、関数がimportできるだけでは完了ではない。
入力ケース、出力、参照値、誤差、実行バージョン、未対応条件を記録して初めて完了とする。
外部参照値が入手できないときはその事実を示し、架空のSUPERFISH/CST比較表を作らない。

最新メッシュ改善の検証: 82テスト、`out/validation-physical-mesh-final-20260906/` PASS。
seed周波数差ゼロ、RF相対差最大6.67e-16。既存ベンチマークの更新なし。
