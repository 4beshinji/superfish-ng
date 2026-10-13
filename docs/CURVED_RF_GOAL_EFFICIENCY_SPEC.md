# RF重み付き版5の固定一般形状対照

2026-10-13 JST、`ADD-N04-rf-goal-01`の仕様受入。
[親N04残件](N04_REMAINING_CARDS.md#add-n04-rf-goal-01)の版5固有の精度・費用比較を具体化する。
本書と[固定入力](../examples/curved_rf_goal_efficiency/plan.json)は計算前の契約であり、
新しい比較器・独立参照package・36実行の受入は後続02〜06である。
全計画と親N04は未完。普遍的効率、収束定理、連続誤差上界はこの有限比較の受入条件ではない。

## 現行経路と今回の不足

公開`curved_rf_adaptive_refinement.validate_request`は版5と二つの明示表面方針を受理する。
`next_plan`/`assemble`/`execute`、`curved_rf_goal_indicator.curved_rf_goal_indicator`は、
元親の一様確認を棄却した後、**その元親**から局所細分へ分岐する。
`max_levels`にはinitial、採用/棄却のuniform_probe、rf_localの全求解eventが入る。
RF指標のR/Q随伴・周波数微分・全要素寄与は優先度であり、物理誤差上界ではない。
表面方針`uniform_when_rf_passes`はRF三量だけが通ったprobeを次親に採用できるが、
そのprobeを成功確認に数えず、二つの全五量確認が必要という公開停止条件を保つ。

N06の`adaptive_efficiency_plan.build_adaptive_efficiency_plan`は版3/4の固定12行、
`adaptive_efficiency_worker.execute_efficiency_worker`はその全行一致を要求する。
`load_efficiency_reference`も元三ケースのCase/初期meshに固定されている。
版5への行変更とprolateの参照要求がどちらもFEM前に拒否されることを今回再現した。
旧workerの直線的な水準列を版5branchへ読み替えない。
既存N05〜N08の受入、旧固定入力、公開版5の選択・求積・peak・停止は変更しない。

## 固定36実行と初期入力

新`examples/curved_rf_goal_efficiency/`の六要求は元入力の全Case、全ID、全壁tagを保持する。
球と丸めはN05計画の要求、長球は`curved_prolate_rf_surface.json`を起点とする。
元暗黙meshを現行の初期計画で一度だけ明示化して保存した。方式ごとに再生成しない。
四つの原入力と六要求のpath/byte数/SHA256を`plan.json`に固定する。
形状は全て合成形状であり、KEK/LANLの測定構造ではない。

| family | 尺度1の解析形状・元mesh | 初期cell / P2節点数 | 全event上限 / cell上限 | 全native ID |
| --- | --- | --- | --- | --- |
| sphere | 半径0.08 m、中心z=0.08 m、元chord許容0.0016 m | 36 / 85 | 8 / 250000 | fundamental |
| prolate | 軸半径0.16 m・径半径0.08 m、中心z=0.16 m、元chord許容0.0016 m | 80 / 181 | 12 / 100000 | fundamental |
| rounded-two-lobe | N05の全丸め輪郭・明示mesh、全長0.21875 m | 1201 / 2502 | 8 / 250000 | target, guard-2, guard-3 |

節点数は拘束前の幾何節点数で、実固有問題の自由度とは区別する。
球のevent/cell予算はN05の8/250000を継承する。元配布例の8/20000とは明示的に異なる。
長球の12/100000は既存RF表面方針例を継承する。予算を失敗後に拡大して元行を置換しない。

各familyについて尺度a=1,2、三方式、独立二反復、計36行を実行する。
順序はfamilyが球→長球→丸め、各family内が尺度1→2、各尺度の反復1が
`uniform`→`rf_goal`→`uniform_when_rf_passes`、反復2は逆順。
各行は別プロセスの新規native初回求解から始め、他行・過去runのFEM解を再利用しない。
全36行で最少36、event予算から最大336回のnative固有求解となる。部分失敗した呼出しも別記する。
随伴線形solve、参照準備、開発/GUI検査の求解数をこのnative固有求解数と混同しない。

尺度2は全曲線座標/半径、元mesh座標、join/gap/chord許容、生成max_edgeを2倍にする。
角度、接続、tag、要素順、ID、求積次数、追跡条件を変えない。
既存長球尺度検証と同じく`normalization_j=a**2`（1/4 J）、beta=1、sigma=5.8e7 S/m、
peak phasorを固定する。全長が変わるため有効加速長・電圧積分区間も相似に変わる。
全方式が同じ尺度の同じ規格化を使い、比較のために場振幅を後からfitしない。

三方式とも元P2写像の制限だけで細分し、解析境界へ再投影しない。
bulk=0.5、最小corner angle=5度、基底q=12/高次q=24、求積許容1e-6、
追跡overlapは球/長球0.95・丸め0.98、margin=0.05、cluster gap=1e-6、
minimum relative singular value=1e-8を維持する。全要求の詳細は六JSONを正とする。
各行のwall上限3600秒、process最大RSS上限32 GiB、BLAS1 thread、同時実行1、CPUのみ。
他の重い検証が終端してから開始する。最大36時間の有限実行枠で、未達も結果に含める。
参照準備は独立の3600秒/32 GiB枠に分け、その準備の中断/不足も記録する。

## 厳密な計画・拒否契約

`plan.json`の版1は専用document_type `curved_rf_goal_efficiency_plan`。
必須top-levelはschema_version、document_type、status、input_sources、cases、executions、
expected_native_executions、limits、resources、normalization、physical_error_bound、
physical_acceptance_status、new_fem_solvesの13項目で、未知/欠落キーを拒否する。
`status=PLANNED`、36行全て`NOT_RUN`、`new_fem_solves=0`、物理上界nullを要求する。
各nested objectも固定fixtureのkey集合/厳密型/値に一致させる。boolをintとして受理しない。
raw JSONの全階層重複、NaN/Infinity、巨大数、空ID、余分/不足/重複の行、順序変更、
予算/許容/方式/親Caseの変更、参照方式への暗黙fallbackをFEM前に拒否する。
schema5要求は公開validatorで再検査し、元sourceと六要求を読取前後で再hashする。
pathはrepository相対、通常fileのみ、絶対path/`..`/symlink/外部pathを拒否する。
pathの見かけだけで同一入力と判断せず、SHA256と全正規化Case/meshも照合する。
全入力はdeepcopyで返し、返却値の変更や呼出し中のsource変更を次回の検査で検出する。

`uniform`は元要求からsurface_refinement_policyだけを除きschema4へ変換して初期nativeを構築し、
常に末尾uniformを追加する専用対照経路。局所指標/随伴計算を架空に加えない。
他二方式はschema5のsurface_refinement_policyを各方式名へ明示設定する。
公開版5validatorが受理することだけで固定比較計画として受理しない。
[拒否例](../examples/curved_rf_goal_efficiency/refusals.json)は各発生段階と必須の結果を固定する。
要求解析・参照束縛の欠陥はactionableなValueError、実行中の不足は元成果物付き非成功状態。

## branchと二種類の停止

新専用workerは公開版5の`next_plan`/`assemble`と`_VerifiedRFPrefix`の意味をそのまま使う。
native eventごとに元parent_event_index、refinement_kind、marked_cells、全current_mode_ids、
採用可否、uniform_confirmations、五量比較、求積、RF指標、元保存path/SHAを残す。
公開`replay_adaptive_refinement`で元checkpoint全文書を再構築し、同一要求・元event列の
公開選択/停止との一致を確認する。独自の指標近似、棄却eventの削除、順位によるID代用は禁止。
不採用probe直後のlocalは直前probeからでなく記録された元親から作られる必要がある。

公開native statusと比較側`accuracy_status`/`benchmark_status`を別欄に置く。
native `TARGETS_MET`はRF五量の二一様確認であり、独立参照や全場精度の合格を意味しない。
比較側の初回達成は**採用event**で全独立ゲートが通る最初のevent。
棄却eventの独立精度も保存し、その先行達成は診断欄だけへ記録する。
確認達成には、実parentの連鎖上の三採用eventが必要で、二辺とも全域uniform、
三点それぞれの独立ゲートと二辺それぞれのRF/peak/場の変化ゲートが全て通ることを要求する。
平坦化した隣接二行、棄却したprobe、rf_localを一様確認として数えない。

nativeが`TARGETS_MET`でも独立条件が未達なら、残予算内で最後の採用eventから
比較専用のuniform continuationを行ってよい。これはterminal公開checkpointのresumeではない。
元公開checkpointは凍結し、別journalに`origin=benchmark_confirmation`、元parent参照、
追加Case/mesh/native、全ID・精度・費用を保存する。公開eventやnative statusを書き換えない。
追加eventも同じmax_events/cell/wall/RSS予算に含める。nativeの他の非成功停止からは続行しない。
一様対照の全eventも同じ独立条件・確認規則・予算で判定する。

`LEVEL_LIMIT`、`REFINEMENT_LIMIT`、`TRACKING_BUDGET`、`ZERO_INDICATOR`、
`QUADRATURE_UNVERIFIED`、`QUANTITY_UNVERIFIED`、ID未確認、例外、資源停止、中断は保持する。
PAUSEDは継続可能な状態であり成功ではない。非有限・欠測値を0誤差へ置き換えない。
現行公開engineにない報告状態は比較journalだけへ置き、公開schemaを暗黙拡張しない。

## 独立精度ゲートと参照の結合

| 指標 | 独立差・二確認変化の相対上限 |
| --- | --- |
| frequency_hz | 1e-4 |
| r_over_q_accelerator_ohm / r_over_q_circuit_ohm | 各0.005 |
| geometry_factor_ohm | 0.005 |
| epk_over_eacc / bpk_over_eacc_mt_per_mv_per_m | 各0.01、native区間の両端 |
| electric_relative_l2 / magnetic_relative_l2 | 各0.005 |
| axis_ez_relative_l2 | 0.01 |

`adaptive_efficiency_accuracy.assess_efficiency_samples`の元nativeノルム分母、全正重み、
Hφから一つだけ決める符号をEr/Ez/Hφ/軸Ezへ共通適用する規則を継承する。
両R/Qの2倍関係は1e-12以内で別検査する。全PEC壁・全体積・全物理軸区間を使う。
主精度ゲートは指定mode_idに対するもの。全native modeの元場・RF・固有値順・個別ID、
参照側の全五modeとTE/TM適格性を保存し、guardの切捨てで指定IDを確定させない。
未確認/真縮退/guard不足はUNVERIFIED。周波数順位だけで参照modeを対応させない。

両Gauss16/24の全点で判定し、全ゲートが両次数で通ること、各相対誤差指標の次数間の
絶対差も当該指標の上限内であることを確認する。異なる点数の配列を直接差し引かない。
点数削減、0.95領域crop、欠測点除外は禁止。
固定native P2領域と解析参照領域の全radial/polar fan対応、正Jacobian、全curve/全区間を束縛する。
異なる領域の体積密度の平方根を用いる既存のL2比較規約を明示し、
円筒成分を保つ。これはMaxwell場のpush-forward、幾何の再投影、振幅fitではない。
軸場は物理z上のEzで比較する。離散peak区間と独立solverの経験的peakを連続最大値の保証と呼ばない。
代数residual・RF指標が小さいことを離散化誤差の証拠に代用しない。

| family | 独立参照と必要な新準備 |
| --- | --- |
| sphere | `analytic_sphere.SphereTM`の数学的TM参照。N06全域Gauss16/24の元packageと数式を再検証し、六要求中の同じ球Case/明示meshへ結合。尺度2の参照は同じ解析式から計算 |
| rounded-two-lobe | N03/A01の独立E空間cavsim2d/NGSolve、h=0.005/0.0025/0.00125 mの全五mode。N06全域packageと元matrixを再hash、同じ元Case/meshと全個別IDを再確認 |
| prolate | N03の`N01-prolate-new`、同じ三h・全五modeを元保存場から評価。ただしN03 native初期chord=0.0001 mと本要求0.0016 mは別P2領域。**本要求の全P2領域へ新しい評価gridを準備し、旧gridの同一視を拒否** |

独立源は既存A01 MIT候補commit `48741ff46ca44463281a5ab5945328615881b502`と
`benchmarks/cavsim2d/a01-20260914.json`、元license/source manifestに結合する。
[参照anchor一覧](../examples/curved_rf_goal_efficiency/reference_sources.json)に現存path/SHAを固定した。
これは後続package準備の入口であり、候補の存在だけで参照精度を受理しない。
新規依存・network・legacy solverは不要。既存隔離環境の保存場を読む。
新packageは元三hの二変化、指定target/guardの実場対応、全E/H・物理軸、両R/Q/G/peak、
元Ue/Uhと規格化を再検査する。原TE/TM全五候補を保持し、N/A量は適格性とともに明示する。
尺度2は尺度1の独立場を明示Maxwell法則で導出できるが、元場/係数・変換式・両側領域を束縛する。
U=a² Jではf→f/a、E/H→E/H/√a、V→√a V、Pwall→√a Pwall、Q→√a Q、
両R/Q/G/正規化peakは不変、体積重み→a³倍、軸積分重み→a倍となる。
全native受入時には同一履歴が得られた対のRF/全E/H相似差1e-8以下を別確認し、
異なる履歴なら同一元P2領域の共通評価点で比較し、この閾値を無理に適用せず差/履歴を報告する。
後者でも各行の独立精度ゲートはそのまま必要である。

元参照/係数/領域が欠ける場合、その量の独立精度はUNVERIFIEDで準備不足を表示する。
本NGの細密解や古い五量集約reportを独立参照に代用しない。
旧prolateの164481 DOF追加一様対照は内部対照であり、独立物理参照ではない。
固定参照の不足を解消できなければ03は未完のまま。閾値・形状・hを変更した追加探索は
別仕様/別outとして元不足を保持し、固定36行の受入へ混ぜない。

## 費用・保存・失敗の契約

`adaptive_efficiency_timing.PhaseRecorder`、`adaptive_efficiency_observation.observe_selected_calls`、
`adaptive_efficiency_process.run_measured_process`を再利用する。
観測だけのwrapperは実関数の引数/結果/例外を変えず、nested費用のinclusiveとexclusiveを分ける。
root時間と内訳を二重加算せず、呼出し0と欠測nullを区別する。
既存N06の観測aliasだけでは版5/随伴が抜けるので、実呼出し元の次を必ず覆う。

| 実処理 | 観測境界 |
| --- | --- |
| FEM固有求解 | `curved_rf_adaptive_refinement.solve`、`curved_solution`の組立/eigsh/規格化 |
| RF goal/随伴 | engineの`curved_rf_goal_indicator`、indicator内`r_over_q_adjoint`/`r_over_q_frequency_derivative`、adjoint内factorization/solveと全要素寄与 |
| branch/追跡/求積/peak | engineの`assemble`/`next_plan`、実`_apply`/`_quality`/`_quadrature`/`_surface`/保存追跡。内部再計算も実回数で残す |
| 保存/再構築 | `save_run`、全native読取、完全checkpoint再構築、reference検査、全場sampling、journal/checkpoint書込 |
| process | spawn前の単調時計から実子終端・reapまで。import、参照読取、最終報告、失敗/中止も含む |

採用/棄却を問わず全eventの求解・検証・RF指標・次計画・保存費用を累積する。
確認probeを次行の費用から落とさず、棄却後の元親復元も数える。
初回達成/確認達成時点のprefix壁時計、FEM内秒、プロセス全体秒、最大RSS、全event最大DOFと
確認採用DOFを別欄に出す。途中失敗の処理秒も残し、最後の成功event費用だけに切り詰めない。
初回/確認達成しない行は当該値null、観測した全費用/最終状態は保持する。
共有参照準備時間、元参考solve費用が欠測ならUNKNOWN、各行の参照検査費用は実測して別報告する。
全体wallを含む比率とFEM経路比率を両方出し、失敗/精度未達の行に成功速度比を付けない。
二反復の両値・範囲・順序を表示し、有利な一回や最終DOFだけを選ばない。
OS/Python/NumPy/SciPy/CPU/visible memory、BLAS環境、時刻、source SHA、終了code/signalを保存する。
元N07の高次組立再利用は限定diagnostic実装であり、版5全体の既存加速と称しない。

保存manifestは元全source、固定plan、reference、全event/native配列、元checkpoint、
比較continuation、費用journal、stdout/stderr/例外、worker/resource実終端を束縛する。
読取再生でFEMを呼ばず、全RF/全mode/元E/H、親連鎖・選択・停止・全誤差を再計算して照合する。
再hashした改変でもCase/元mesh/branch/ID/fieldの内容から検出する。
中止/再開は原prefixを保持する別実行として記録し、無中断の36計測行と混ぜない。
既存outを上書きしない。完成済み数値は表示/文書/監査修正だけのために再求解しない。

## 保存する既存の非優位・未達

旧残差適応の球/長球は一般優位を示していない。
長球の旧12eventの`rf_goal`は両尺度LEVEL_LIMIT。
拡大48event要求は尺度1で中断され、verified checkpoint 27/求解完了28、尺度2未実行である。
48event完走・成功と書き換えない。
明示表面方針の両尺度6event、7232 cell/14665 DOFのnative TARGETS_METと、
旧104.942/105.398秒は有用な先行結果だが、今回の独立参照付き交互二反復速度比ではない。
N06の円筒/丸めで一様が有利だった結果、球で適応が有利だった条件も保持する。
詳細は[旧表面方針](CURVED_RF_SURFACE_POLICY.md)、[非球形比較](CURVED_NONSPHERE_COMPARISON.md)、
[N06受入](N06_ACCEPTANCE.md)。今回の三方式で優位がなくても有限比較を正しく報告すれば受入可能。

## 必須五工程

| カード | 先行 | 責任・受入 |
| --- | --- | --- |
| ADD-N04-rf-goal-02 | 01 | 新`curved_rf_goal_efficiency_plan`のstrict固定計画/36行構築。型/重複/未知/予算/順序/改変/入力コピーと六要求を新unittestで検査。旧N05計画は不変 |
| ADD-N04-rf-goal-03 | 02 | 新`curved_rf_goal_efficiency_reference`の全域参照package/読取・尺度・実ID・元source束縛。球の独立解析式、長球/丸めの三h全mode、全E/H/物理軸/Gauss16/24/両R/Q/peakを確認。参照不足時は未受入 |
| ADD-N04-rf-goal-04 | 03 | 新`curved_rf_goal_efficiency_worker`/保存journalと専用script CLI。版5元branch/公開replay・uniform continuation・全event観測/費用・失敗/中止再開を実workerとunittestで確認。native選択/停止不変を元公開engineへ照合 |
| ADD-N04-rf-goal-05 | 04 | 新`scripts/validate_curved_rf_goal_efficiency.py`で固定36行を新outへ順次実行。全元native/全誤差/独立参照/相似/全event費用・未達・二反復を保存。数値未達は改善して消さず結果として報告 |
| ADD-N04-rf-goal-06 | 05 | 全36行の完全再生、元版5GUIで採用/棄却branchと元全場・RF、両表面方針、保存復元/未達表示を実Chromeで確認。04の実中止/再開と元byte証拠を結合、全handle終端・source/全原条件監査、親N04四群の最終再照合 |

02の直接消費checkは`test_adaptive_efficiency_plan`と公開版5のmetadata検査。
03はaccuracy/fields/domain/analytic_grid、04はtiming/observation/process/workerと
`test_curved_rf_adaptive_refinement`/`test_curved_rf_goal_indicator`/`test_curved_rf_adjoint`から
変更経路に対応する個別caseを選ぶ。実装前に失敗する独立不変量/反例を記録する。
幾何不変量は元全P2境界・Green面積/体積/∫r³、親子制限のK/M、Maxwell相似を分離する。
03/04で科学共有核を変更する必要が生じた場合はその影響範囲の独立validator/seed規則を適用し、
初めからfullを走らせない。節目のfullはV03へ接続し、既存成功証拠を再利用する。
06のGUIはbenchmark専用Web機能の新設を要求しない。既存版5checkpointの表示を検査し、
比較専用continuation/費用は別journal/CLI出力で照合する。製品表示に意味変更が必要なら個別修正として検証する。
06まで親N04はIN_PROGRESS。V03/V05の依存に06を追加し、仕様01だけで親を閉じない。

## 仕様段階の確認と来歴

rawは`out/n04-rf-goal-spec-20261013/`。
`build_spec_inputs.py`は四箇所のsolve禁止guardの下で六初期空間/両方針を構築した。
初回は独立体積積分helperの戻り値の取扱いでValueError、FEM0・生成要求0。
元scriptと`probe-initial-error.log`を保全し、点/重みから三積分を正しく集計して再実行した。
`probe.json`/`probe.log`は終了0、六caseの全接続/座標相似、面積4・体積8・∫r³の32倍、
Green対別P2積分の最大相対差6.662e-16（gate1e-12）、現行六拒否例を確認した。
元1458対象源は全byte不変。新七JSON追加後1465で、製品FEM/RF/公開停止の変更はない。

`reference-inventory.json`ではN06三anchorの元SHA一致、N03長球三h各五modeの保存file現存、
独立MIT候補の元79 source SHA一致と旧未達reportの現存を確認した。
これはinventoryであり新grid・参照場・native精度の検証ではない。
今回の新FEM、unit、seed、full、実GUI、legacy実行は全て0。
外部論文/sourceの新取得なし。既存N03/N05/A01と元数学/現代MIT依存の来歴を継承する。
