# D05：RF探索の量・能力・未評価条件

2026-10-07、D05の仕様カード。目的量/制約の定義・単位・方向・能力とN/A、
初期/候補/最終の独立三水準、未確認候補を採用しない条件を固定する。
既存要求版1〜3と保存再生の意味は維持する。本仕様の受入は追加物理の探索実装受入ではない。
原D03の一般形状/追加物理・保存/操作はD06〜D11で続行し、静的設計/熱はL02/L03へ分ける。

## 現行と追加評価の能力表

「定義あり」は実FEM場/RFの物理量として存在することで、探索APIへの接続済みを意味しない。
現行 `rf_design` の六量と、`rf_optimization` のclosed native曲線P2真空axis TMだけを接続済みとする。
一般TM形状はD06、軸対称TE/平面はD08、真空/内導体/確認済み材料HφはD09。
条件付きR/Qは宣言した真空軸経路・元SI/peak規格化から取得する。N/Aのnullを0へ換算しない。

| 物理/幾何 | f / G / Qwall | U / Pwallの単位 | 加速器・回路R/Q | Epk/Eacc・Bpk/Eacc | 現行探索/後続 |
|---|---|---|---|---|---|
| axis接続真空m=0 TM | 定義あり | J / W、実入力領域 | 宣言した加速経路と規約で定義 | Eaccが非零で有効な表面包絡/収束がある場合 | native曲線P2の既存六量は接続済み。一般形状D06、Qwall追加は後述 |
| axis対称m=0 TE | 定義あり | J / W、実入力領域 | N/A、軸方向Eが恒等的0 | N/A、加速Eaccがない | D08、現行RF探索へ通さない |
| Cartesian遮断TE/TM、矩形/多角形/全二次領域 | 定義あり | J/m / W/m、側壁だけ | N/A、有限加速経路がない | N/A、加速Eaccがない | D08。TEとTMの壁H接線/元領域をそれぞれ使う |
| 同軸/正半径で真空軸経路がないHφ | 定義あり | J / W、全PEC壁 | N/A、軸が導体内/計算域外 | N/A、加速Eaccがない | D09。TEMの存在を加速器R/Qへ読み替えない |
| axis接続・穴付き/曲線の真空Hφ | 定義あり | J / W、全PEC壁 | 元Caseで有効な真空軸経路がある場合だけ | 専用の収束した表面包絡がない量は評価未実装 | D09、穴/境界componentを省略しない |
| 確認済み実数・無損失・等方材料Hφ | 定義あり、Qは壁損失だけ | J / W、各領域を含む全周量 | 宣言した全区間が真空軸の場合だけ。経路なしはN/A、不正経路は入力拒否 | 現行専用RFに必要なピーク評価が未実装 | D09、H17の追加体積/複素損失を推定して加えない |

参照する源は [rf](../src/superfish_ng/rf.py)、[TE](../src/superfish_ng/te.py)、
[planar](../src/superfish_ng/planar.py)、[curved planar](../src/superfish_ng/planar_curved_solver.py)、
[coaxial](../src/superfish_ng/coaxial.py)、[material Hφ](../src/superfish_ng/material_hphi_rf.py)。
Hφの能力/真空軸判定は[正半径](HPHI_MESH_RF.md)、[軸接続](AXIS_HPHI_RF.md)、
[曲線](CURVED_HPHI_RF.md)と[材料契約](MATERIAL_HPHI_RF_PLAN.md)も用いる。
材料 `volume_loss_w=0` は無損失媒質の入力契約であり、総Qや小さい材料損失の測定ではない。
[H17](MATERIAL_HPHI_LOSS_SCOPE.md)の採否待ちを探索の新機能として数えない。

物理的N/A、実装未対応、数値未確認を別に記録する。
N/A/未対応量をobjective/constraintに指定した要求は**FEM前に拒否**し、理由と選べる量を示す。
元場/診断に量が存在しても、その量に必要な収束評価が未実装なら選択能力へ入れない。
全出力のnull/理由を保持し、N/Aの制約を無条件METへしたり削除したりしない。

## 名称・単位・最大最小

現行criteriaの名称は次の六量だけ。[定義と評価](RF_DESIGN_CRITERIA.md)と一致する。
raw RFの `*_estimate` 名をcriteriaの名前と混同しない。表面比は元場からの有限離散包絡を使う。

| criteria quantity | 単位・定義 | directionと適用 |
|---|---|---|
| frequency_hz | Hz、追跡した実正FEM固有周波数 | 明示minimize/maximize。目標帯は独立にlower/upperで制約 |
| r_over_q_accelerator_ohm | Ω、abs(Vacc)^2/(omega U) | 明示minimize/maximize、有効な加速経路のみ |
| r_over_q_circuit_ohm | Ω、abs(Vacc)^2/(2 omega U) | 明示minimize/maximize、同じVacc/U。加速器定義の半分 |
| geometry_factor_ohm | Ω、Qwall Rs = 2 omega U / integral(abs(Ht)^2 dS) | 明示minimize/maximize、全PEC壁。平面はU′/全側壁dsへ同時に替える |
| epk_over_eacc | 1、元離散表面abs(E)包絡/(abs(Vacc)/L) | 明示minimize/maximize。有効非零Eaccと独立表面評価が必須 |
| bpk_over_eacc_mt_per_mv_per_m | mT/(MV/m)、元離散B表面包絡/Eacc | 明示minimize/maximize。T/(V/m)から係数1e9、有効非零Eaccが必須 |

どの量も一つの目的だけを持ち、最大/最小を暗黙に決めない。上下限は同じ量の閉区間で、
正確な名称/単位・finite非負値・bool拒否・重複拒否を維持する。基準値と改善量も量の単位で宣言する。

追加物理では次の取得量をD08/D09の評価へ必要な範囲で接続する。
現行六量の辞書にこれらが受理済みであるとは主張しない。

| 追加評価quantity | 単位/定義 | 使える条件と収束対象 |
|---|---|---|
| q0 | 1、omega U/Pwall。平面はomega U′/P′wall | 正の全壁loss、固定の壁sigma/媒質。壁だけのQと保存。f/U/Pの三水準を別に確認 |
| stored_energy_j / stored_energy_j_per_m | J / J/m、peak E/H energy合計 | 入力の規格化固定値であり、規格化を変えて有利にできる自由な目的量にはしない。RF再検証に必要 |
| wall_loss_w / wall_loss_w_per_m | W / W/m、Rs/2×全壁abs(Ht)^2積分 | 固定規格化/同じsigma/同じ全壁定義。取得・Q評価/収束に必要。採用する場合は物理別の単位付き評価器が必須 |
| absolute E/B surface peak | V/m / T、選択した実離散場の全PEC表面 | 元RFに共通の有効ピーク包絡がない物理は未実装として選択拒否。単なる点sample/既存estimateを能力へ昇格しない |

Qwallを総Q、U′をU、P′をPにalias化しない。phaseはpeak exp(+iωt)、B=mu0 Hは真空/非磁性壁に
対応する定義で、材料内部のBには実mu_rを含める。原則として新しい物理量を黙って計算/保存しない。
絶対peakを将来評価する際も固定U（3D）/U′（平面）を要求し、規格化の変更で制約を通せないようにする。
鋭角の有限離散peakと連続問題の特異性は別であり、物理peakの精度を保証する量として売り込まない。

## 未確認・未収束の状態

量の取得と包絡の評価は同じ元native、選択個別ID、SI規約、実入力領域に束縛する。
欠落/非有限/負のエネルギー・loss/ゼロfrequency、未確認ID/guard/真縮退、求積未解決、
形状不正/予算不足/solver失敗は評価対象へ進めず、有利な目的値を返さない。
有効な真空軸電圧が数学的に0となる場合のR/Q=0と、経路不存在のN/Aを区別する。
Eaccが0/不安定な比の目的には進めない。

現行 `_evaluate_design` は全三水準の観測包絡が揃い、refinementがTARGETS_METの場合だけ採用可能。
制約の全包絡がinclusive bounds内ならMET、全包絡が外ならVIOLATED、境界をまたぐならUNRESOLVED、
必要区間がなければUNVERIFIED。局所のMET表示は観測包絡の範囲検査だけであり、
refinement未確認時の全体UNVERIFIED/eligible_value=nullを覆さない。
`rf_optimization_search.restoration_value` も先にrefinement/UNVERIFIEDを確認してnullへする。
未収束包絡の中心値/下限/上限を、成功・違反量0・best objectiveとして採用しない。

将来の物理別評価器も同じ採用条件を満たす。制約未確認はnull/理由、境界をまたぐものはUNRESOLVED。
VIOLATED/UNRESOLVEDの有限包絡は、全収束・個別ID確認済みなら違反量の改善に使える。
境界をまたぐUNRESOLVEDも包絡のはみ出しを減らす比較対象であり、制約MET/目的採用値にはならない。
各constraint_scalesで単位付き違反距離を割った最大値を減らし、制約を全て満たした後にだけ目的の改善を比較する。
minimizeは包絡上端、maximizeは下端を保守的採用値とする。未評価を±infinity/0で代用しない。
この有限観測包絡を連続問題の誤差上界/連続最適性の保証とは呼ばない。

## 初期・候補・最終の独立三水準

既存要求1〜3の初期/各候補は元の固定形状・固定履歴＋uniform 0/1/2の三つの実FEM。
最終候補は同じ固定形状/履歴＋uniform 1/2/3を新規に求解する。元場のコピーや解析倍率を新solveへ数えない。
変数の初期/最終が同じ場合でも、最終専用三水準の評価/creatorを保存する。
探索予算には初期・全候補・最終の試行を含め、既存上限3×max_trialsと再開の既実施trial数を維持する。

追加物理は、各nativeの全領域/材料界面/PEC/元basisを保つ専用細分を使う。
各三水準のf・元E/H/個別ID・Ue/Um/U・全壁loss・必要RF量を別に確認する。
求積増次数の整合、代数残差、fine/coarse差を互いの代用や連続物理誤差上界としない。
各量の数値基準は専用validator/宣言したtargetsから取得し、f gateだけでRF/場/peakを合格にしない。
追加評価のtargetsには必要量ごとの有限な正基準と相対/絶対SI差の扱いを明示し、
旧版1〜3の五量/二変化/peak区間基準を変更しない。未実装の量はtargetsを形だけ作って通さない。

最終native/全三水準/元IDの再生が未確認ならFINAL_UNVERIFIED、条件未達ならFINAL_CRITERIA_FAILED。
粗いsearch候補の成功や小さいalgebraic residualを最終成功へ持ち越さない。
SEARCH_COMPLETEは宣言した有限探索と最終設計条件の終了で、全設計空間の大域最適性ではない。

## 独立対照と後続カード

一般TMの既存曲線三水準/旧要求1〜3をD06/D07で保持し、閉PEC円筒/球など適用可能な解析と元E/H/RFを別確認する。
D08は円筒TE/矩形遮断TE・TMの二尺度と独立Bessel/矩形解析、側壁/端板の違い・理由付きN/Aを確認する。
D09は同軸TEM/TM、一様無損失材料、二層を使い、実f/場/全壁loss/保存再生と有効/不正真空軸経路を確認する。
各専用解析は検査だけに使い、FEM/場や探索目的値の代用にしない。

真空の同一形状一様尺度sでf→f/s、固定3DUではE/H→s^(-3/2)、固定U′ではE/H→s^(-1)、
G不変・固定sigmaでQwall→sqrt(s)が独立尺度対照。R/Q尺度則は同じ実加速経路とphase変換がある場合だけ。
材料/伝搬/開放/異なる規格化へこれを自動適用しない。
静的磁石の多極/力/目的場/非線形失敗はL02、温度/熱収支/RF源移送はL03の別仕様。
最適化の運用/全trial/保存/中止再開/GUIと親監査はD10-TE/D10-planar/D10-hphi/D10-operations/D11。
D05の表だけをそれらの受入へ数えない。

## 今回の受入と来歴

製品/テスト/scriptは変更せず、現行source/strict拒否/採用predicateと上記各RF量を読取照合した。
[前回full](PLANAR_CURVED_TRACKING_TUNING_ACCEPTANCE.md)のsourceと現在の関連科学源は同一。
既存fullの `test_rf_design` / `test_rf_optimization` 等の実結果は証拠として再利用し、文書用に再実行しない。
この仕様受入は新FEM/unit/専用validator/seed/全検証/旧版実行0。
raw監査は `out/d05-rf-optimization-scope-20261007/acceptance.json`。
各D05原条件、全ローカルリンク、RF名称/units/状態/後続依存、全123カードのD05だけの変更と関連源不変を確認する。
新外部資料・コード/依存・legacy source/binary参照・Hosted CI・GPUはなし。
D05 DONEは親D03/全goalの完了ではなく、既存六量・追加能力の必要仕様を固定した結果である。
