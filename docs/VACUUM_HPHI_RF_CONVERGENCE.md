# D09：直線真空Hφの三水準とRF制約

現在のD09全原条件監査は **DONE**。[条件別受入](HPHI_RF_DESIGN_ACCEPTANCE.md)を参照。以下の限定受入/未完記述は当時の履歴。探索運用D10-hphiと全goalは継続。

`VacuumHphiConvergence` は同軸、正半径一般領域、軸接続領域の元Project三件と
隣接E/H追跡二件を要求する。[専用RF観測](HPHI_RF_DESIGN.md)、
[材料三水準](MATERIAL_HPHI_RF_CONVERGENCE.md)、[D05量/採用契約](RF_OPTIMIZATION_SCOPE.md)の後続。
完全な元固定領域・全PEC壁・既存P1/P2 FEMを使う。D09の曲線側と全条件監査、
D10-hphiの実探索/所有checkpointは後続で、この入口だけで完了にはしない。

## 宣言と入口

`vacuum_hphi_convergence.VacuumHphiConvergence(convergence, tracking_requests, mode_id, max_sample_points)`。
convergenceは既存 `HphiConvergence`、Projectはちょうど三件。選択mode_ranksは初期IDの順位だけ。
tracking_requestsは元両側を同じ全真空領域上の明示有限比較空間へ投影する
`HphiTrackingRequest` 二件。geometry_mappingは固定領域のため拒否する。
初期個別ID集合を保ち、後続は実current IDsの順位を継承する。
初期順位を後続順位へ固定せず、各水準の実追跡IDからRFと元場を選ぶ。
追跡帯の上には最終を含む各元FEMの実求解済みguardを要求する。
比較空間は固有FEMの代用/追加水準ではない。

既存 `HphiConvergence` が全ordered外輪郭/穴、元次数/求積、spectrum数、U[J]、
壁sigma、有効真空軸経路の一致と、要素数増加/最大辺長減少を検査する。
同じ初期IDを失った際に順位/周波数/新ラベルで置換しない。
追跡overlap/margin/gapは収束宣言より弱くできず、overlay/候補/Gram予算もその範囲内。
material/curved Caseは型エラーで専用adapterへ案内する。

```python
from superfish_ng.rf_optimization import (
    assess_vacuum_hphi_rf_design, save_vacuum_hphi_rf_design,
    read_vacuum_hphi_rf_design)
report = assess_vacuum_hphi_rf_design(native_runs, convergence, criteria)
saved = save_vacuum_hphi_rf_design(native_runs, convergence, criteria, "new-assessment.json")
replayed = read_vacuum_hphi_rf_design("new-assessment.json")
```

元15ファイルhash・Caseと能力を検査し、元K/M・最低正帯・場を再構築する。
N/Aの軸無し両R/Q、未実装peak/追加損失/総Q/自由Uの目的はFEM再構築前に拒否する。
両R/Qは有効な明示真空軸pathの場合だけ取得し、Q0は全PEC壁摂動損失だけ。

## 独立のID・数値gate

元EとHを別に追跡し、両方で同一個別ID・共通係数phase・有限guardを要求する。
集合だけの対応、近縮退、有限projection/予算未解決はUNVERIFIED。
完全な元セルoverlay上で元EとHの差を直接積分し、2*pi*r dr dzの各細側L2 normで割る。
真空の一定epsilon0/mu0は各比で相殺される。Gram差の相殺から差を推定しない。
実追跡の最終求積次数と追加2次数の直接差を比較し、1e-10超の差は未確認で止める。

f、E、H、Ue/Um/U、Pwall/Rs/Qwall/G、全original PEC segment/componentのPwall、
存在する両R/Q、共通phase付き複素Vaccを別々に判定する。
最後二変化が非増加かつ既存量別閾値内の場合だけPASS。
軸edgeの壁lossは幾何上0であり、削除せず元ordered segmentとして保持する。
小さい代数残差・固定U・ID対応だけを場/RF精度の証拠にしない。
精度は有限三標本の経験的判定で、連続誤差上界/表面peak精度の保証ではない。

## 制約と全保存

三水準のmin/max包絡と明示方向/閉区間を比較する。
全包絡の包含だけMET、全外VIOLATED、境界横断UNRESOLVED、系列欠落UNVERIFIED。
全必須数値gate PASSの場合だけrefinement_status=TARGETS_MET。
数値未確認の局所METは全体UNVERIFIEDとeligible_value=nullを覆さない。
全数値gateと全制約がMETならCRITERIA_MET、minimizeは包絡上端、maximizeは下端を採用する。
physical_error_boundはnull。既存TM optimizer版1–3の対象/数学/許容差は変えない。

保存は元全15hash・全宣言/追跡/選択元RF・量別gate・包絡/判定を新規ファイルへ出力する。
native内部への書込み/上書きは拒否し、評価中/公開直前の元変異も再hashで拒否する。
相対参照bundleの移動後も全再構築し、型を含む完全なcanonical JSON比較を行う。
保存されたPASS/採用値/ID/型の主張を信用しない。

## 検査と来歴

rawは `out/d09-vacuum-rf-convergence-20261007/`。
欠落していたAPIのimport終了1を先に保全した。
新 `test_vacuum_hphi_rf_design` は独立同軸TEMのf/H/Er/全壁loss、
独立円筒TM010 Besselのf/H/Ez/全壁loss/両R/Q、一般穴領域の全壁保持を分けて検査する。
strict事前拒否、guard/予算/数値未達、phase反転、保存移動/型偽装/元の遅い変異も確認する。
直接消費先は `test_hphi_rf_design test_hphi_tracking test_hphi_field_overlap`。
独立解析解は検査専用。FEMを置換せず、既存自作の元場/専用追跡/有限projection/nativeを再利用する。
新外部資料・依存・legacy参照/旧実行・GPU・Hosted CIはなし。

2026-10-07限定受入：新同軸1件25.044秒、軸/一般穴2件96.598秒、残新4件210.948秒、
追加実ID継承1件58.180秒、直接消費17件54.389秒は全実終了0。合計25検査を分割受入した。
元数値snapshotの全1174 Python源を固定し、終端後に追加した独立ID継承test源一件も別hashで固定した。
追加検査は実三mode/二個別IDを追跡し、同じ集合でも後続の宣言順序を実current IDsから変更できないことを確認。
一般穴の粗三水準は実f/E/局所壁gate未達、元八壁/二componentを保持してUNVERIFIED。
既存422製品源中420不変、旧RF評価定義の全AST同一/旧optimizerは三import追加のみ。
旧材料受入/単一観測の数学と全123台帳は維持、D09と全goalは継続。
全コマンドのlog/終了/hash/source/台帳監査は同rootの `acceptance.json`。
全handle（65549/13316/25719/88073/5458）は実終端、生存処理/worker/browserなし。
新seed/full/専用validator/旧実行0。seed TMの数値pathは未変更、既存milestone fullを再実行しない。
