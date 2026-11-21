# D09：専用HφのRF量取得・能力判定

現在のD09全原条件監査は **DONE**。[条件別受入](HPHI_RF_DESIGN_ACCEPTANCE.md)を参照。以下の限定受入/未完記述は当時の履歴。探索運用D10-hphiと全goalは継続。

[材料専用三水準・制約](MATERIAL_HPHI_RF_CONVERGENCE.md)を限定受入。新6＋直接消費15＋追加メタデータ拒否1の22検査を分割受入し、全handle終端。材料以外の三水準接続/D09全受入は続く。以下は単一観測入口の受入履歴と契約。

[直線真空三水準/個別ID・制約](VACUUM_HPHI_RF_CONVERGENCE.md)も限定受入。新8＋直接消費17の25検査は分割PASS。曲線三水準とD09全条件監査は後続。

2026-10-07、D09の第一実装。真空同軸/正半径一般mesh/軸接続/曲線/確認済み材料の
五種類のnativeを、[D05の量・未確認条件](RF_OPTIMIZATION_SCOPE.md)へ接続する。
単一保存FEMの観測入口を受入し、三水準収束/個別ID/最終採用評価は続行する。
**D09はIN_PROGRESS**。D10-hphiの探索/全trial/worker/CLI/GUI/所有checkpointは後続。

## APIと厳密な能力

`hphi_rf_design.hphi_rf_capabilities(case)` と `validate_hphi_rf_criteria(case, criteria)` は
元Caseの物理/全領域/真空軸経路を解析し、FEMなしで能力を判定する。
既存 `rf_optimization` から下記観測/保存/再生/criteria検査を呼べる。
要求版1〜3のTM探索入力・既存六量・探索判断は変更していない。

```python
from superfish_ng.rf_optimization import (
    observe_hphi_rf_design, save_hphi_rf_design, read_hphi_rf_design)
criteria = {
    "schema_version": 1,
    "objective": {"quantity": "q0", "direction": "maximize"},
    "constraints": [{"quantity": "frequency_hz", "lower": 0}],
}
report = observe_hphi_rf_design("native-run", criteria, mode_rank=1)
saved = save_hphi_rf_design("native-run", criteria, "new-observation.json")
replayed = read_hphi_rf_design("new-observation.json")
```

| 量 | 単位 | 能力/意味 |
|---|---|---|
| frequency_hz | Hz | 実保存FEMの最低正スペクトルから選んだrank |
| geometry_factor_ohm | ohm | 全PEC壁、全3DのUとH接線積分 |
| q0 | 1 | omega U/Pwall、壁損失だけ。材料の総Qではない |
| wall_loss_w | W | 固定U[J]・sigma・非磁性壁金属のRsから得る全PEC壁損失 |
| r_over_q_accelerator_ohm | ohm | 元Caseに有効な真空軸区間がある場合だけ、abs(Vacc)^2/(omega U) |
| r_over_q_circuit_ohm | ohm | 同じVacc/U、加速器定義の半分 |

目的方向は明示minimize/maximize、一つの目的と非空制約リスト、finite非負のinclusive bounds。
未知項目/alias/bool/NaN/Inf/重複/逆区間は拒否する。
軸なしの両R/Q、非真空加速区間、未実装ピーク、total_q/追加体積損失、
自由目的としてのstored_energy_jは理由と選択可能な量を示して拒否する。
観測入口はCase/criteria/rankを検査してから行列/元場を再構築する。
将来の求解入口は同じcriteria事前検査を**solve前**に使う必要があり、D10接続済みとは数えない。
材料losslessの `volume_loss_w=0` と理由付きR/Q nullはraw RFにそのまま保持する。
[H17の追加損失採否](MATERIAL_HPHI_LOSS_SCOPE.md)を推定して採用しない。

## 元場・保存と未評価

元native五ファイルの全hashを開始/終端で確認し、専用readerで幾何・材料・K/M・最低正帯・
係数・SI/peak規約・全RFを完全再構築する。全壁segment/component、材料region、
軸電圧と規格化をraw RFに残し、元Case/規約/全hashも観測文書へ保存する。
元nativeは変更せず、native内への観測保存を拒否する。出力は新規だけ。
保存参照は文書からの相対path。同じbundleを移動した後も全再構築できる。
元sourceを所有コピーする機能はこの入口にはなく、参照が失われた場合は再生を拒否する。
保存値/criteria/Case/hash/採用値/型/余分な項目の変更も全体再構築照合で拒否する。

`mode_rank` は正固有周波数の順位であり、ラベル/個別IDではない。
`mode_identity=null`、refinement/statusはUNVERIFIED、全constraintもUNVERIFIED、
包絡とeligible_valueはnull。観測値が設計bounds内でもMET/最終成功を返さない。
単一場の再構築や小さい代数残差を、離散化誤差/三水準収束/連続物理精度の証拠へしない。

D09の続きは、専用の同一全領域三水準、E/Hの別比較・個別ID/guard、
f/Ue/Um/U/全壁segment/RFの最後二変化、inclusive観測包絡と全体採用条件の接続。
材料/曲線を直線真空の収束器へ通さず、全元材料界面/二次幾何を保持する。
旧TM表面包絡の条件や許容差を緩めず、未実装ピークは拒否を続ける。

## 検査と来歴

入口欠落は `rf_optimization` からのimport終了1で先に記録した。
数値拡張の独立対照は同軸TEMのf=c/(2L)、Hphi=C/r cos(pi z/L)、
C^2=2U/(mu0 pi L log(b/a))と全四壁の閉式積分。
二尺度でf→f/s、固定Uの壁P→P/s^(3/2)、G不変、Qwall→Qwall sqrt(s)を別確認した。
一様実数材料epsilon_r=4/mu_r=9のf/6・H/3・壁損失/Q/G則と、
二層の独立TEM参照のf・元H/Er・全壁lossも別検査した。
解析は検査のみで、製品は専用FEM/元RFを使う。

`test_hphi_rf_design` 新6件は9.674秒/終了0。全五native・有効軸両R/Q・単一場未採用、
求解再構築前のstrict拒否、移動/改変/boolean偽装/遅いsource変化を確認した。
rawは `out/d09-hphi-rf-observation-20261007/selected-new-tests.log`。
直接利用先 `test_rf_design` 全5、旧RF探索のstrict/未確認採用拒否2、
`test_material_hphi` 全6、材料native完全再生/再hash改変拒否2、`test_hphi_convergence` 全3の
計18件は51.316秒/終了0。既存六量と専用RF/保存/収束器の直接消費先を確認し、
新seed/full/専用validatorは実行していない。結果とsource/台帳監査は同rootの `direct-consumers.log` / `acceptance.json`。
新源は自作adapter、既存専用parser/native/FEM/RFのみを再利用し、核/物理許容差を変更しない。
新外部資料・依存/legacy source/binary・旧版実行/Hosted CI/GPUなし。
D09の三水準受入と親D03/全123カードgoalは未完了。
