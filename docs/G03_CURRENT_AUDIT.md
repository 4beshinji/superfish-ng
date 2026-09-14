# G03の現行要件照合

2026-09-14 JST、開始HEAD d8855b0。前段階の構築版10を含む実装を、
[COMPATIBILITY_PLAN.mdのG03/N03行](COMPATIBILITY_PLAN.md)と
[CONIC_GEOMETRY.mdの番号付き5段階](CONIC_GEOMETRY.md)に照合した。
G03を全計画から切り離して完了へ読み替えず、旧入力との対応と物理精度も残す。

## 要件と現在の証拠

| 要件 | 実装・直接の検査 | 現在の判定 |
|---|---|---|
| 1. 円/楕円/双曲線の点・接線・曲率、弦誤差、面積モーメント | conics.py。test_conics.pyの陰関数/微分直交/頂点半径/向き/面積/尺度/弦距離。解析体積とモーメントはcurved_contour.py | nativeの有限弧を限定受入。旧NT=2/3の意味とは別 |
| 2. 接続・正半径/軸・交差/接触/微小隙間 | check_curve_join、curve_bounds/curved_contourの全辺対・軸鎖/タグ/向き拒否。test_curved_contour.pyのinvalid_topology_gaps_tags_and_orientation | 完成輪郭を検査。接線角は許容差による数値検査、座標を勝手に修復しない |
| 3. 元曲線/許容差のCase・保存・GUI | test_curved_saved.pyの場を再求解しないnative再読込、再構築した幾何/係数/RF/宣言の改変拒否。構築1〜10/診断1〜13とCase適用 | 保存/操作の専用範囲を受入。新構築10の実Chrome初回/実再起動・全21組の保存バイト一致を確認済み |
| 4. 曲線写像・正Jacobian・写像に一致するFEM/場/RF | curved_space/curved_fem/curved_solution/curved_rf。test_curved_femの物理線形場、test_curved_solutionのエネルギー/連鎖律、test_curved_rfの独立壁積分 | P2場/二次多項式写像を限定受入。解析楕円そのものの厳密なFEM表現とはしない |
| 5. 幾何細分とFEM細分を独立に変えるf/場/RF | test_curved_refinementの写像/勾配制限、Galerkinエネルギー、元二次境界保持。過去の楕円/双曲線3幾何×2FEM結果を今回読み直した | 過去のf/場/RFと面積/体積はPASS。表面ピークの連続2区間と幾何差は下記で補った |
| 曲率・最小丸め半径 | meridional_radius.py、test_meridional_radius.pyの厳密円・有限非円極値・予算不足・PEC角拒否・構築/保存/鏡映、test_conic_scale.pyの極端な尺度 | PECの最小子午面半径を限定受入。周方向主曲率・物理ピーク上界は含まない |
| 接線・指定半径フィレット | 接線構築1/2、固定直線と弧3、線分間4、従来区間探索5/6、全代数元点対の直線/円錐曲線7、円/非円8、円/円9、非円/非円10 | 円/楕円/双曲線の有限候補を製品経路へ接続済み。無限対・予算/出力精度不足・空保持を選択可能にしない |
| 弧端・退化・重解・中心重複 | 診断13までの円/線/非円の全根・有限所属・元平方根符号、同一支持/反対枝、カスプ、潰れ円と元点対/中心数 | 各分類器の適用条件と完全性フラグを保持する。全入力で有限時間内のPASSを約束しない |
| 旧曲線指定との対応 | LEGACY_INPUT.mdとlegacy_input.pyはNT=2/3等を明示拒否。COMPATIBILITY_BASELINE.mdのK02はR25の種別記録のみ | 未完。対象7.17の入力変数/既定値/枝/接線操作を版付きで確認し、変換と幾何/FEM比較が必要 |
| 物理表面ピーク | 球の独立解析解、固定二次楕円体の細分/追加一様参照、連続離散ピーク囲み、元PEC角/軸極診断 | 離散上下界・小残差・固定領域比較は一般物理誤差の証明ではない。非球形の幾何を含む検証を拡充する |

ソースとテスト名はそれぞれsrc/superfish_ng/とtests/を指す。
今回これらの既存テスト内容を読み直したが、全既存検査を再実行したという記録ではない。
旧[照合表](G03_ACCEPTANCE.md)の「一般重解/新フィレット未接続」は構築10までの専用範囲では解消した。

## 残件を決めた実行記録

out/validation-g03-native-geometry-separated-20260908/comparison.jsonは現存しPASS。
楕円の各幾何の細FEMは1440/4644/13452要素、双曲線は864/2172/7684要素。
両形状とも幾何モーメント差の減少、固定幾何FEM比較、最終幾何間のf/場/RFが合格している。
ただし同報告のphysical_peak_convergenceは明示UNVERIFIEDである。
各形状・幾何にはFEM2水準があり、results.jsonには連続離散ピークの上下界もある。
2水準だけではN03の連続2細分区間条件を確認できない。

out/n03-surface-convergence-final-20260908/validation.jsonは球の独立解析五量との比較でPASS。
SURFACE_CONVERGENCE.mdの現在の製品評価は同じ二次境界と3水準以上の固定幾何履歴を要求し、
geometry_approximation_assessed=Falseを保持する。幾何を変えた系列をこのAPIへ混ぜない。
CURVED_RF_SURFACE_POLICY.mdの非球形の成功も、固定二次領域上の追加一様対照との差である。

今回、保存Caseから再評価した楕円はSMOOTH_WITHIN_TOLERANCE、双曲線例はUNVERIFIED_GEOMETRYだった。
双曲線のf/RF差が小さくても、角のあるその形状を滑らかな表面ピーク合格例へ変換しない。
境界診断と最初の楕円native再検証はout/g03-separated-surface-20260914/baseline.json。

## 今回選んだ不足と検証方法

G03/N03の楕円1例について、幾何3水準それぞれのFEM2水準を現在のnative readerで再検証し、
同じ元メッシュ・二次境界のまま第3FEM水準を新しく求解する。
既存6結果を新規solveと数えず、元ファイルのSHAと全再検証、追加3solveを分けて記録する。
受入条件は各幾何のFEM2区間と、最細FEM同士の幾何2区間で、
f 1e−4、加速器R/QとG .005、Epk/EaccとBpk/Eacc .01以下。
ピーク比は上下界の最悪相対差。モードは比較した場の重なり/競合・軸場/RFで確認し、順位一致だけを根拠にしない。
保存例の計算スペクトルは1モードであり、未計算モードとの分離を証明する検査ではない。

独立な幾何不変量は楕円の連続面積πab/2、回転体積4πab²/3と二次写像の積分。
境界の角度幅hに対し、二次補間の連続位置誤差はmax(a,b)|h|³/(72√3)以下。
140桁の元曲線と保存節点の差にLagrangeのLebesgue定数5/4を掛けて加え、保存多項式の節点丸めも分ける。
幾何3水準で位置上界・面積/体積差が減少すること、各固定二次領域の面積/体積不変を確認する。
FEM親子のRitz関係、高次積分のRayleigh/質量形式と壁損失も別に確認する。
この補間評価は新しい形式検証済み超越関数実装ではない。

実行器はscripts/validate_geometry_surface_convergence.py。
専用検証は577.959秒、終了0でPASS。元6nativeを再検証し、追加3FEMを別保存した。
全9結果、固定幾何FEM6区間、最細FEM同士の幾何2区間を確認した。
元アーカイブと988ファイルのsrc/tests/scripts/examplesは開始終了で不変。
新規3solveの要素数は5,760/18,576/53,808。初回実行で全条件が合格した。

| 量 | FEMの全6区間での最大相対差 | 幾何の2区間での最大相対差 | 基準 |
|---|---:|---:|---:|
| 周波数 | 9.22138e-07 | 1.45429e-06 | 0.0001 |
| 加速器R/Q | 0.000487695 | 4.63382e-06 | 0.005 |
| G | 1.1054e-05 | 5.00928e-08 | 0.005 |
| Epk/Eacc | 0.000483994 | 6.85165e-05 | 0.01 |
| Bpk/Eacc | 0.000430406 | 5.69834e-06 | 0.01 |


境界位置上界は6.07011e−6、7.58764e−7、9.94340e−8 mへ減少。
連続面積に対する二次領域差は3.09300e−6→1.93479e−7→1.28814e−8、
体積差は4.63737e−6→2.90185e−7→1.93216e−8。
各固定領域の面積/体積、Ritz関係と高次積分の条件も合格した。
12/16次形式からのRayleigh周波数差は最大1.146e−13、質量差6.662e−16、8/16次壁積分のG差2.221e−16。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_geometry_surface_convergence.py \
  --archive out/validation-g03-native-geometry-separated-20260908 \
  --out out/g03-separated-surface-new
```

既存出力先を上書きしない。報告はout/g03-separated-surface-independent-20260914/report.json、
元ファイルのhashは同archive-provenance.json、次作業を含む索引はout/g03-separated-surface-20260914/acceptance.json。
製品ソース/FEM/保存契約/許容差/benchmarksは変更していない。
既存unit・seed・全validate・Hosted CI・GUIをこの文書/専用検証器変更のために再実行してはいない。
本検査を、独立な非球形Maxwell参照や一般形状の物理ピーク誤差上界の代用にはしない。

## 次の完了に必要な証拠

G03は部分受入のまま。今回の専用検証が合格しても、旧曲線入力対応と一般物理精度の未確認を残す。
次はC00/K02とC02の対象版入力仕様を確認して、NT=2/3の支持曲線・端点・枝・既定値とnative表現を対応付ける。
既存inventoryが記録する/tmp/superfish-wine-runtime/input-spec/SFCODES.txtは現在存在しない。
付属公式SFCODES.DOCまたは公開仕様を改めて探し、欠けた抽出文書から既定値を推定しない。
公開数学/仕様と許可済みのblack-box入力/設定/数値出力を使い、旧ソルバーコード/バイナリの内部は調べない。
未確認を除外済みに変えず、変換を実装した場合は独立幾何と新旧の両側細分を検証する。
親33課題の完了数をこのG03内の進展だけで増やさない。C00.Vと利用者業務V02も含む全計画goalは継続する。
