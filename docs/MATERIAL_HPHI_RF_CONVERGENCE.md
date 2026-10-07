# D09：材料Hφの三水準とRF制約

`MaterialHphiConvergence` は専用材料Project三件と隣接E/H追跡宣言二件を要求する。
[単一native観測](HPHI_RF_DESIGN.md)の後続で、元の固定全領域・全材料界面・全PEC壁を保ち、
元FEMから個別ID/有限guard・場・RF収束を再検証する。[D05](RF_OPTIMIZATION_SCOPE.md)の採用契約に従う。
D09の真空/内導体/曲線側の三水準接続と全条件受入、D10-hphiの実探索/所有運用は続く。

## 宣言と入口

`material_hphi_convergence.MaterialHphiConvergence(projects, tracking_requests, mode_id, thresholds)`。
projectsは三つの実 `HphiProject(MaterialHphiCase)`、tracking_requestsは二つの
`MaterialHphiTrackingRequest`。各宣言には隣接全partitionのsame_domain比較と、
両側元partitionから明示した有限P2比較空間へのresolution宣言が必要。
隣接のmaterial/region対応は同じIDへのidentityだけを受理し、名前を入れ替えて領域量を混同する宣言は拒否する。
幾何・材料・region ID・元P1/P2・求積・モード数・U[J]・壁sigma・真空軸経路は全水準で固定。
各次メッシュは要素数増加と最大辺長減少を要求し、全domain/界面の一致は専用overlayで検査する。
初期ID集合を固定し、後続宣言は実追跡のcurrent IDsを元順位どおり継承する。
最終水準を含め、追跡帯の上に実求解済みguard modeと有限比較空間の宣言を必須とする。
resolution用空間はFEM固有解の代用/四つ目の解ではない。

既存 `rf_optimization` から次のAPIを利用できる。

```python
from superfish_ng.rf_optimization import (
    assess_material_hphi_rf_design, save_material_hphi_rf_design,
    read_material_hphi_rf_design)
# convergenceは上記の厳密宣言、criteriaはD09専用のquantity/方向/閉区間。
report = assess_material_hphi_rf_design(native_runs, convergence, criteria)
saved = save_material_hphi_rf_design(native_runs, convergence, criteria, "new-assessment.json")
replayed = read_material_hphi_rf_design("new-assessment.json")
```

能力/rank/Caseの事前検査と、全元native五ファイルhash・K/M・最低正帯・元場の再構築を保つ。
軸無しR/Q・不正/非真空軸・未実装ピーク/追加体積損失の拒否/N/Aは維持する。
新しい材料損失・総Qは導入せず、Q0は全PEC壁摂動損失だけ。

## IDと独立の収束

隣接二組で元E/Hを別割当し、同じ単一ID・共通係数phase・有限guardを要求する。
近縮退・集合だけの継承・有限projection未解決・比較予算不足では選択RF系列を完成させずUNVERIFIED。
新しいラベル/周波数一致/順位を、失われたIDの代わりにしない。実再構築不一致は拒否する。
これは三つの離散標本の個別対応で、標本間の連続分枝保証ではない。

場差は元セルの片側E/Hを完全なsame_domain共通分割で直接積分する。
体積密度は2*pi*r、Eはepsilon0*epsilon_r、Hはmu0*mu_r。共通phaseを適用し、
細メッシュの各エネルギーL2ノルムで割る。Gram差の相殺から場差を推定しない。
元追跡の最終積分次数と追加2次数を照合し、相対場差の差1e-10超は未確認で止める。

f、E/H直接差、Ue/Um/U、Pwall/Rs/Qwall/G、存在する両R/Q、
全PEC segment/componentのH積分、各material regionのUe/Um/U・隣接壁loss、
有効な共通phase付き複素Vaccを別々に比較する。
最後二変化は非増加かつ宣言した専用閾値内が必要。
求積整合/小さい代数残差/固定Uをf・場・壁loss収束の代用にしない。
既存 `HphiConvergenceThresholds` の値を維持し、f/場/RF/Vaccの閾値を分ける。
追跡のoverlap/margin/gapをこの宣言より弱くできない。

## 制約・保存

元三水準の量のmin/maxを観測包絡として保存し、inclusive boundsの全体包含だけをMETにする。
全包絡が外ならVIOLATED、境界をまたぐならUNRESOLVED、必要系列欠落はUNVERIFIED。
全必須数値gateがPASSの場合だけrefinement_status=TARGETS_MET。
数値未達時の局所METは全体UNVERIFIED/eligible_value=nullを覆さない。
全数値gate＋全制約METがCRITERIA_METで、minimizeは包絡上端・maximizeは下端を採用する。
観測包絡を連続誤差上界/精度証明とは呼ばず、物理誤差上界はnull。

保存は全宣言/元15ファイルhash・実追跡/元RF・全量gate・包絡/判定を含む新規ファイルのみ。
元native内への保存を拒否し、相対参照bundleを移動しても全再構築する。
値・型・採用/収束判定・ID・hash・元native・余分な項目の変更は拒否する。
所有コピー/探索checkpointの運用はD10-hphiであり、この入口だけで完了にしない。

## 検査と来歴

受入コマンド/実結果・source/台帳の最終照合は
`out/d09-material-rf-convergence-20261007/acceptance.json` と同rootのlogへ記録する。
欠落していた専用評価入口はimport終了1で先に記録した。
独立二層TEMのf・元H/Er・全壁lossを三つの実FEMで別比較し、各誤差の減少も要求する。
phase反転、有限guard/予算/厳しい数値gate、ID入替え、境界をまたぐ制約、
未収束の局所MET、全保存/移動/型偽装の拒否も検査する。
既存自作material比較/元場/追跡・有限projection/native/RFを再利用し、科学核/既存許容差を変更しない。
解析は検査だけ。新外部資料・依存/legacy参照/旧実行/Hosted CI/GPUはなし。

2026-10-07限定受入：新物理1件103.018秒＋残新5件1168.208秒、直接消費15件61.074秒は実終了0。
新6件は三水準の独立二層f/H・Er/壁loss、strict/有限guard/予算/数値未達・ID置換・包絡・phase・保存再生/偽装を確認。
直接消費先は `test_hphi_rf_design` 全6、`test_material_hphi_tracking` 全4、`test_material_hphi_field_overlap` 全5。
全field/RFの数値段階をarchiveへ保全した後、同じregion IDの体積が半減する対応入替えの反例を再現。
初回/tmp runnerのroot import欠落ERRORと、本来の独立体積不変量AssertionError（いずれも終了1）を保全し、
隣接のidentity対応拒否Ifだけを追加した。正常identity構成と不正alias拒否の新1件7.140秒/終了0、FEM0。
新/関連の全22件を分割受入した。旧全数値/その他ASTと元テストはarchive同一、追加Ifは正常fixtureでfalse。
この拒否修正のためにFEM/物理再生を重複実行しない。中間snapshot1368 hashはarchive/現行の適用範囲を分けて照合した。
全handle（86913/59982/40228/16673/42743）は実終端。新seed/full/専用validator/旧実行は0。
メタデータ型/region量の検査と三水準数値証拠を区別し、材料以外の三水準とD09全条件は続ける。
