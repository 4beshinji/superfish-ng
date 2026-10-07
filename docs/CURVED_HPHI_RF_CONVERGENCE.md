# D09：曲線Hφの実個別IDと三水準RF制約

現在のD09全原条件監査は **DONE**。[条件別受入](HPHI_RF_DESIGN_ACCEPTANCE.md)を参照。以下の限定受入/未完記述は当時の履歴。探索運用D10-hphiと全goalは継続。

`CurvedHphiRFConvergence` は元の完全二次領域・全native chartを保持する三水準RF評価。
[単一観測](HPHI_RF_DESIGN.md)、[材料三水準](MATERIAL_HPHI_RF_CONVERGENCE.md)、
[直線真空三水準](VACUUM_HPHI_RF_CONVERGENCE.md)の後続で、[D05量/採用契約](RF_OPTIMIZATION_SCOPE.md)に従う。
既存[曲線三水準診断](CURVED_HPHI_CONVERGENCE.md)の同順位対応を個別IDとは見なさず、
元E/Hの実追跡と有限比較空間のguardを別に評価する。D09全条件監査とD10-hphi探索/所有運用は後続。

## 宣言とAPI

`curved_hphi_rf_convergence.CurvedHphiRFConvergence(convergence, tracking_requests, mode_id)`。
convergenceは既存 `CurvedHphiConvergence`、ちょうど三件の元 `HphiProject(CurvedHphiCase)` と
完全P2参照幾何・水準ごとの元native chartを含む。
元次数/求積・mode数・U[J]・壁sigma・有効真空軸経路は固定。
元幾何の全二次係数・全domain/穴/軸役割の一致と細分条件を既存宣言から再検証する。
初期選択mode_ranksは初期IDの順位だけで、後続の順位を固定しない。

tracking_requestsは隣接二組の `CurvedHphiTrackingRequest`。
両側のdomainは同じ完全参照のsame_vacuumだけ。
previous/current native_cellsは元収束宣言と同じものを要求する。
comparison geometry/chartは各元全領域を覆う明示した有限比較空間で、追加の固有解水準ではない。
比較空間のbinary64丸め宣言は既存専用比較の契約で検査するが、元三水準の幾何一致を弱めない。
初期個別ID集合/追跡prefix数を固定し、次のprevious IDsは実current IDsの順位を継承する。
各元水準の追跡帯上に実求解済みguardを必須とし、集合対応だけでは採用しない。
追跡overlap/margin/gapを量別収束宣言より弱くできず、候補/overlay/Gram/求積標本予算も超えられない。

```python
from superfish_ng.rf_optimization import (
    assess_curved_hphi_rf_design, save_curved_hphi_rf_design,
    read_curved_hphi_rf_design)
report = assess_curved_hphi_rf_design(native_runs, convergence, criteria)
saved = save_curved_hphi_rf_design(native_runs, convergence, criteria, "new-assessment.json")
replayed = read_curved_hphi_rf_design("new-assessment.json")
```

全元15ファイルhash・Case/能力を事前照合し、元K/M/最低正帯・全space/元E/Hを再構築する。
元全PEC壁のQ0を使い、追加体積/複素損失や総Qは受入済みモデルがないため拒否する。
有効な明示真空軸pathの場合だけ両R/Qを取得し、軸無しのN/Aは維持。
不正能力、未実装peak、自由U目的をFEM再構築前に拒否する。

## 元P2場・全壁と独立gate

各隣接組で元EとHを別々に追跡し、同じ個別IDと一つの係数phaseを要求する。
個別対応/有限guardが未確認なら系列を補完せずUNVERIFIED。
初期と後続の実rankをそれぞれ元場/元RFへ渡し、周波数/新ラベル/同順位で代用しない。

元全二次overlayでEとHの直接差を別積分し、実3D体積2*pi*r dr dzの各細側L2 normで割る。
両nativeの完全な二次写像・元係数を使う。弦/頂点線形化/解析場への置換はしない。
実追跡の最終積分次数と追加2次数を比較し、差1e-10超は未確認で止める。

各元曲線PEC辺の元H積分は完全P2参照境界のordered segmentへ正確なchartで集約する。
既存 `_level_rf` は選択した実rankで求積整合と全component再現を再検証し、
全segment/componentの壁P=Rs*H²積分/2を取得する。元native RFを変更/置換しない。
軸edgeは0壁lossの役割を保持し、穴を削除しない。

f、E/H、Ue/Um/U、Pwall/Rs/Qwall/G、全参照segment/componentのPwall、
存在する両R/Q、共通phase付き複素Vaccを別判定する。
最後二変化の非増加と既存量別閾値内の場合だけPASS。
小さい残差・固定U・ID対応だけを場/RF精度とは呼ばない。
これは固定P2領域の有限三標本で、解析境界への幾何誤差、連続誤差上界、表面peak精度は保証しない。

## 制約・全再生

三水準min/maxの経験的包絡と明示方向/inclusive boundsを比較する。
全包絡包含だけMET、全外VIOLATED、境界横断UNRESOLVED、系列不足UNVERIFIED。
全必須数値gate PASSだけrefinement_status=TARGETS_MET。
数値未確認の局所METは全体UNVERIFIED/eligible_value=nullを覆さない。
全数値gateと全制約METでCRITERIA_MET、minimizeは包絡上端、maximizeは下端を採用する。
physical_error_bound=null、geometry_approximation_assessed=false。

元native外に新規ファイルだけを保存し、全宣言/hash・実ID/guard/元RF・量別gate・包絡/判定を含める。
評価中/公開直前の元変異を拒否する。相対参照bundleを移動しても全元FEMを再構築する。
保存PASS/採用値/ID/型/余分な項目は完全canonical JSON比較で検証し、入力の主張を信用しない。
旧単一/材料/直線RF評価の数学と、TM optimizer版1–3の対象/量/判断は変更しない。

## 検査と来歴

rawは `out/d09-curved-rf-convergence-20261007/`。欠落していたAPIのimport終了1を先に保全した。
新 `test_curved_hphi_rf_design` は解析TEMを元P2空間でf/H/Er/全壁lossと別に照合し、
真正の曲線軸/正半径・穴付き全domainでは全壁/両R/Q/元RF・体積と固定Uの尺度則を検査する。
解析TEMケースは幾何上直線の二次要素であり、真正の曲線ケースとは別に記録する。
strict/全参照/chart/能力、guard/予算/数値未達、phase、全保存移動/型偽装/遅い元変異も検査する。
直接消費先は専用曲線追跡、全参照壁の既存収束、既存元場の独立積分。
独立解析/尺度式は検査だけ。自作の完全幾何比較・元場/有限projection・追跡・壁/RF再生を再利用する。
新外部資料・依存・legacy参照/旧実行・GPU・Hosted CIはなし。

数値第一段階の実終端：解析TEM新1件383.850秒、真正曲線axis/正半径・穴2件268.615秒、
直接消費8件264.043秒は全実終了0。TEM f/H/Er/壁loss誤差は全三水準で減少。
真正曲線の粗三水準は個別ID成立でもf/E/局所壁・有効なVacc/RQ等が未達でUNVERIFIED。
初期1177 Python源と数値段階archiveを保全した後、同じ有理点を1/2と2/4で表すだけで
chartが拒否される反例を、元P2係数/全Project/親role不変・FEM0で再現（終了1）。
元trackingと同じ有理数正規化で照合する事前述語だけを修正し、新1件33.204秒（FEM0）は終了0。
異なる親roleは引き続き拒否。数値/旧テスト/その他全ASTは不変、元正常chartは既にFraction既約表記。
archive/現行の初回読取監査ERRORも保全し、結合先の誤りだけを修正して監査終了0。
現行1178 Python源を再固定し、残る新4件のstrict/guard・予算/phase/保存移動・改変拒否を実行した。
全件実終了0で終端を回収。実handle/終端は同rootの `observed-handles.json`。

後続の原D05/D09監査では同軸TMも確認した。既存自作Bessel基準のPEC・閉式/独立Gauss半径積分・
Ue=UmをFEM0で照合後、別一時runnerから三つの実原FEMを保存した。初回はNumPy scalarの
制約入力がstrict APIで拒否（検査runner ERROR、終了1）されたため、その原nativeを全再構築して再利用。
同じ値をPython floatで渡した追加1件49.705秒は終了0。新原solve呼出し0、元solve_coaxial3件、
有限比較空間の計算/元FEM再構築は実行し、解析をsolverに渡していない。
TMのf/H/E/Pwall誤差は三水準で減少、四つのordered PEC損失を各々独立解析へ相対0.005で照合。
新RF入口の全gateと保存完全再生も確認し、原15ファイルhashを保持した。
raw/script/hashは同rootの `annular-tm-receipt.json` / `annular-tm/` に保全。
曲線strict684.926秒・guard/予算741.300秒・phase560.070秒の新各1件も実終了0。
曲線保存完全再生handle3558も新1件1925.090秒、実終了0。全handle終端/live=[]。


最終限定監査は `acceptance.json` / `audit.log`、新8＋直接消費8＋追加TM1の17件を受入。
旧423製品源の421はbyte不変、既存RF評価は三関数追記のみ、optimizerは三import追加のみ。
科学核・旧定義・数値閾値と全123台帳は不変。新full/seed/legacy0、D09全条件監査は別に行う。

専用 `scripts/validate_hphi_rf_annular_tm.py` は全数値handle終端後に配置。
成功TM検査coreと元三solve creatorのAST/byte結合を保存し、CLI help終了0と既存出力拒否終了1（FEM0）を確認。
元全15ファイルと全出力byteは保持した。配置したCLI全体の新規数値実行は繰り返していない。
将来の再検証は未使用の出力先で実行する：

```sh
OPENBLAS_NUM_THREADS=1 UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_hphi_rf_annular_tm.py --out out/annular-tm-rf-new
```

実検査の分割コマンドは共通runner
`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v`
に、raw各logに記載した `test_curved_hphi_rf_design` / `test_curved_hphi_rf_chart_semantics` の個別ケースと直接消費8ケースを指定した。
TMはrawへ保全した一時runnerとresume runnerを同じuv環境で実行。全コマンド/源結合/終端は各receiptで保存。
過去の解析/元場検査を新しい全検証数へ加算せず、数値未達もPASSへ変更しない。
