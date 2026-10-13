# RF版5対照worker：比較指標と採用祖先

2026-10-13 JST、`ADD-N04-rf-goal-04` **IN_PROGRESS**。
[原仕様](CURVED_RF_GOAL_EFFICIENCY_SPEC.md)のうち、比較側の全量指標と停止判定を実装した。
新`curved_rf_goal_efficiency_metrics.py`は純粋な数値/記録集約で、FEMを実行しない。
[新規native実行](CURVED_RF_GOAL_EFFICIENCY_EXECUTION.md)も接続し、12新FEMの公開分岐/全場を確認した。
専用CLI/全比較journalの完全再生、別uniform continuationの実証、全観測/実中止再開は未完であり、
04の完了条件は保留する。
36実行05・GUI/全条件06・親N04と全goalは継続。

## 実装した入口

| API | 入力と責任 |
| --- | --- |
| `assess_rf_goal_pair(previous, current)` | 同じ全域gridの元場/物理軸/正重み/両R/Q/G/f/両peak区間を比較。前場ノルム分母、Hφから一つの符号、RFはcurrent/previous、peakは両区間の最悪相対差 |
| `assess_rf_goal_orders(orders)` | 順序付きGauss16/24の九量指標を結合。元閾値・全誤差・各gateとstatusを再照合し、次数間のスカラー誤差差も判定 |
| `assess_rf_goal_history(events, observations)` | 元index/親index/採用可否を保持し、初回採用達成・棄却eventの診断達成・実祖先の二一様辺確認を別々に返す |

pairの各入力は`fields`（N×3）、`axis_ez`、`weights`、`axis_weights`、`quantities`、
`peak_intervals`。前後で異なる重み・欠測・非有限・未解決peakはUNVERIFIED/nullとする。
異なるGauss次数の点配列を直接比較しない。2%の全振幅差は前場ノルムで2%の誤差となる。
磁場だけから得た一つの符号を全E/H/軸Ezへ使い、電場だけの逆符号をfitで救済しない。

ordersの要素は`order`と既存`assess_efficiency_samples`または新pairの`accuracy`結果。
誤差を変更してPASS/gateを据え置いた入力、次数の欠落/反転/重複、bool次数は拒否する。
statusを持つだけの不完全な指標を合格へ扱わない。

historyは元公開eventの`index`、`parent_event_index`、`refinement_kind`、`accepted`、
`status`、`current_mode_ids`、`mode_index`、`quadrature_check`を読む。
各observationは`index`、`source_domain_identity_status`（PASS/UNVERIFIED）、
`reference_orders`、`parent_change`の四項目。parent_changeは初回だけnull、
以後は実`parent_event_index`と二次数`orders`を保持する。
workerは元保存場からこれらを作り、完全再生でも再計算しなければならない。
この集約器だけではsource/全領域被覆/物理IDを認証しない。

確認達成には三つの採用event全てで独立精度・source/domain/ID・求積が必要で、
実親の二辺ともuniform_probeまたは別記録uniform_confirmationで、全九量の変化が必要。
棄却probeとrf_localは一様辺へ数えない。棄却probe直後の局所eventは同じ元親へ戻る。
nativeのTARGETS_MET・uniform_confirmationsを比較側成功の代用にしない。
未確定IDのnullはUNVERIFIEDの非採用eventだけで保持し、重複した既知IDや架空の完全IDは拒否する。

## 検証・未受入範囲

新9＋直接利用先`test_adaptive_efficiency_accuracy`の8、計17個別unitを分割受入。
初回新8＋旧8は16件0.013秒・終了0。実追跡のnull IDを再現した追加1件は修正前ERROR、
修正後の新branch全5件は0.011秒・終了0。変更はhistoryの未確定ID検査だけで、他数値関数と先行testのASTは不変。
初回の成功metric4＋旧8を重複実行せず、その証拠を再利用する。

前場ノルム/2%振幅・共通符号/逆電場・両R/Qの2倍関係・両peak端点・欠測/ゼロ重みを別検査。
三祖先の各点、二辺、source/ID、求積のどれかが未達なら確認達成しない。
棄却probe→元親local→一様1辺では未達、そこから一様2辺目で実祖先[2,3,4]だけが確認となる。
これは比較側の必要条件検査であり、新nativeの精度または公開engineとの分岐一致の受入ではない。

rawは`out/n04-rf-goal-worker-20261013/`。未実装import ERROR、null IDの修正前ERRORを保全。
uv/unittest、BLAS1、`PYTHONPATH=src:tests`で対象moduleと関連8件だけを実行した。
元1473対象源は全byte不変、新module/testを加えて1475。新FEM/seed/full/CLI/GUI/36benchmarkは0。
公開版5の選択/停止、旧N05/06 worker、原閾値は変更しない。

全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45。
次は新規実行の元prefixを保つ全journal再生/再開、追加一様確認、全観測/CLIを完成する。
