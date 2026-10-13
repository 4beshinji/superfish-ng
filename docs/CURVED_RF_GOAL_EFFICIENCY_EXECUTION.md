# RF版5対照：新規native実行と全域場の接続

2026-10-13 JST、`ADD-N04-rf-goal-04` **IN_PROGRESS**。
[比較指標/採用祖先判定](CURVED_RF_GOAL_EFFICIENCY_WORKER.md)を、実FEM・公開版5の分岐・元保存場へ接続した。
新`curved_rf_goal_efficiency_worker.execute_curved_rf_goal_efficiency_worker`は固定36行の一行を受け、
新規directoryにnative、公開checkpoint、全場sample、比較journal、観測費用を保存する。
開発検証は球三方式と長球rf_goalの各3event、計12新FEM。全36実行の受入ではない。

[全journalの保存再検証](CURVED_RF_GOAL_EFFICIENCY_REPLAY.md)は全12event/両次数全場の一致、6改変拒否を確認した。
[実SIGINT/二段階再開・別uniform continuation](CURVED_RF_GOAL_EFFICIENCY_RESUME.md)も無中断の全場/RF一致を確認した。
04の残件は専用CLI、資源停止/部分書込の範囲、
随伴のC線形solve境界を含む全費用の最終確認である。05/06・親N04・全goalは未完。

## 実行の意味

`execution`と`directory`が必須。任意`bindings`は03で固定した参照manifestの同一byte移設、
`max_new_events`は開発用途中停止、`submission_origin`は外側supervisorの単調時計始点である。
変更した行・bool/0/非整数のevent上限・非有限時刻・既存outをFEM前に拒否する。
開発上限は元event上限を拡大せず、比較条件を満たさない途中停止をPAUSEDとして保持する。
独立参照の読取/全SHA検査を先に行い、各行は新しいnative初回求解を使う。

RF二方式は公開`curved_rf_adaptive_refinement.assemble`と`_VerifiedRFPrefix`を直接呼ぶ。
公開eventの全内容を保存し、最後にcacheを使わない公開`replay_adaptive_refinement`で完全一致を確認する。
一様対照は元P2制限による一様計画だけを作り、局所指標/随伴を呼ばない。
同じ元Case/source/全ID・求積12/24・元許容1e-6でRayleigh/massと両R/Q/Gを確認する。
新nativeは元solver/save/readを通し、全P2境界、元Case/source、実親の追跡、幾何積分/Ritzを別検査する。
旧N05/06のworkerやその許容は変更していない。

全native modeのEr/Ez/Hφと物理軸Ezを、03のGauss16/24全点へ評価して保存する。
正体積密度平方根はvolumeだけへ適用し、物理軸を振幅fitしない。
初期の実Hφを全独立候補へ対応させ、宣言IDに対応する実候補・overlap・marginを両次数で確認する。
全候補をpackageに保持し、Hφノルム0のTE候補はnull列として明示する。
後続IDは元親との公開個別追跡から継承する。周波数順位は物理IDの代用にしない。

比較は実parent_event_indexの保存sampleを再読取/再hashして行う。
native TARGETS_METと比較側の状態は別欄に保存し、独立初回達成と三採用祖先確認も別にする。
公開成功後に比較の確認が必要なら、元公開checkpointを凍結して別`benchmark_confirmation`へ
一様追加する実装を置いた。この追加経路の実証と保存再生は残件で、今回の3eventには含めない。
nativeの他の非成功停止からは継続しない。元event/cell予算を全追加eventへ適用する。

保存は排他的作成。各nativeの全file SHA、sample SHA、参照依存、全実装SHAを保存し、
終了時には元固定plan/全要求/原入力の再検査も行う。
例外は元objectをそのまま伝え、終了済みprefix・部分phase費用・attempted/completed求解数をfailureに残す。
元例外を成功statusや0秒へ置換しない。

## 実測した開発prefix

各行を別プロセスで順次実行し、BLAS1・3600秒/32 GiB上限を使った。
process wallにはimport/worker後の追加読取検査/終了も含むため、固定benchmarkの方式速度比には使わない。

| ケース/方式（全て尺度1） | event要素数 | probe全process秒 | worker観測秒 | 最大RSS byte |
| --- | --- | --- | --- | --- |
| sphere / rf_goal | 36→144→576 | 31.432 | 24.449 | 103342080 |
| sphere / uniform | 36→144→576 | 16.946 | 16.238 | 101117952 |
| sphere / uniform_when_rf_passes | 36→144→576 | 31.380 | 24.451 | 103333888 |
| prolate / rf_goal | 80→320（棄却）→113 | 442.077 | 436.086 | 562429952 |

四processは全てPROCESS_EXITED/終了0。球二RF方式のnative statusはTARGETS_METだが、
比較側は初回達成index1・確認未達のPAUSED。一様も比較側は同じ未達を保持する。
球の全3eventの独立解析周波数差は最大4.523e-5、最終全E相対L2はGauss16で0.002894、24で0.002936。
全E/H/軸/両R/Q/G/peakの個別誤差は元journalへ保存し、周波数だけを精度証拠にしない。
全12nativeのUe/Uhはそれぞれ0.5 Jに対し相対差最大1.777e-15。
この離散エネルギー関係を、独立参照に対する離散化誤差と混同しない。

長球はevent1のuniform_probeが不採用となり、event2のrf_localはevent0を親にする。
要素数320のprobeから局所細分したものではない。独立精度の初回/確認達成はいずれもnullを保持する。
全3eventで体積157184/353664点・軸9824/14736点を使い、source/domain/実IDは全てPASS。
元公開checkpointをFEM禁止guardの下でも完全再構築し、全event内容が一致した。

観測は公開再構築で再計算された仕事も含む。長球の元workerではRF指標2回、随伴4回、
factorization4回、周波数微分2回、全要素寄与640回を記録した。
native求解/eigshは各3回。一様のRF指標/随伴は0回である。
inclusive/exclusiveとroot費用を区別する。C拡張SuperLU.solveの単独計測は未接続であり、
factorizationを線形solve全体の時間と呼ばない。全費用要件の受入は04後続に残す。

## 検査・修正・証拠再利用

新worker入力1件（0.908秒）、新native peak結合1＋関連metric4の5件（0.002秒）、
新終端/固定入力guard2件（0.586秒）の計8個別unitがPASS。
元17件の採用祖先/指標受入とは重複を区別し、新規件数へ足さない。
実nativeのpeak scalar名はestimate付きで、比較器が要求する独立peak名とは異なる。
先にその結合をFAILで再現し、前peak区間の下端を既存sample APIの一時基準へ渡し、
最終値は元の両区間上限で再計算するよう修正した。estimate値を採用せず、両端/許容は維持する。

別の制御失敗検査はFEM呼出し直前に元RuntimeErrorを発生させ、同じ例外object・空の完了prefix、
attempted1/completed0、FAILEDの部分費用、全観測aliasの復元を確認した。新FEMは0。
一様の未確認量をQUANTITY_UNVERIFIEDとして止める判定と、終端の固定入力再検査も追加した。
成功12native時点のworker全byteを保存し、そのSHAを当時のsource snapshotと照合する。
後の変更はこの二つの記録/停止guardだけで、全数値helperのASTは不変。
保存12eventへ新停止判定を適用し、元状態の完全一致と元固定要求をFEM0で確認して証拠を再利用する。

rawは`out/n04-rf-goal-worker-native-20261013/`。
初回未実装import、peak結合FAIL、supervisor引数形式の誤記（spawn前）、guard未実装ERRORを保全する。
各新規outは一度だけ使用した。全旧1475対象源のうち変更はmetric結合の一源だけで、
他1474源byteは不変、新worker/testの二源を加えて1477。元FEM/RF/公開分岐/許容/固定要求は不変。
全handleは終端、seed/full/新依存/legacy/GUI/固定36benchmarkは0。
最終metadata監査は`acceptance.json`、ローカルコミット結合は`commit.json`へ保存する。

全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45。
次は全journalの完全再生、元prefixを保つ再開、追加一様確認と実中止、全観測/CLIを完成する。
