# 平面曲線の所有二点比較と独立追跡履歴

2026-10-07、P09の有界leaf。対象は完全なCase版3のCartesian P2 native。
受入条件は、元nativeの全byte/場/RFと作成来歴を保った二点比較の所有保存、
隣接native・追跡帯・ID集合の連続性、実際の過去解へのanchor束縛、
回復後の継承と新所有先への延長、移動後の全履歴物理再生である。
P09はIN_PROGRESS。CLI-worker・実取消し/管理器再起動・実GUI・P09全条件監査は次に進める。

## 所有二点比較

`planar_curved_tracking_saved.execute_owned_planar_curved_tracking(previous,current,request,new_directory)`
は専用 `PlanarCurvedTrackingRequest` を受け取り、両元nativeと全E/H・有限guardを検証してから
新規保存先を作る。`read_owned_planar_curved_tracking(directory)` は同じ物理検査を全て再実行する。
cached報告やmanifestのhash一致だけをPASSの根拠にしない。

保存先には `tracking.json`、`sources.json`、`tracking-results.json`、`manifest.json` と
`previous/`、`current/` を置く。native入力は元五ファイルをそのまま所有する。
完了済み平面job入力は元Project/job/manifestと `solution/` の五native、計八ファイルを保ち、
存在する `worker.claim` も元byteでコピーする。import済みjobにclaimを発明しない。
Projectの表示単位やcreator/import来歴も保持する。外側の補助 `log.txt` は物理operandに含めない。
コピー先に新しいFEM求解を帰属させず、SI、単位長peak +i phasor、両R/QのN/Aも元nativeのまま保つ。

専用manifestは `superfish_ng_owned_planar_curved_tracking` / `saved_version=1`。
全request・元operand・結果hash、作成実装hash、`source_changed_during_run=false` を保存する。
sourcesの元pathは情報だけであり、公開readは元pathを開かない。
所有先の余分ファイルやsymlinkを拒否する。コピー各側の前後に加えて、
全側のコピー後と完了時にも全元source hashを確認する。検出時に有効manifestを出版しない。

## 履歴と回復

`planar_curved_tracking_history.PlanarCurvedTrackingHistoryRequest(step_count,max_steps=100,identity_recoveries=())`
は専用 `history_version=1` のstrict要求で、正の整数count/budgetと明示した順序付き回復配列を持つ。
回復配置は `after_step_index` と専用 `PlanarCurvedIdentityRecoveryRequest`。
bool版/整数、余分key、重複・逆順配置、将来のanchorを拒否する。

`execute_owned_planar_curved_history(pairs,request,new_directory)` は先に全二点比較を物理再生する。
隣接stepの元五nativeが完全一致し、tracked countと継承したID/ID集合が一致する必要がある。
未解決集合を次stepの新個別IDで置き換えることはできない。
前stepがUNVERIFIEDなら続行しない。各二点が単独PASSでも履歴の成立を保証しない。

snapshot 0は最初のprevious、snapshot k+1はstep kのcurrentである。
初期anchorは、実有限群がsingletonで元個別IDが確定した場合だけresolvedとする。
後続anchorは実際にPASSした個別対応/回復のsnapshotに限る。
宣言したanchor IDをこの実履歴へ束縛し、anchor→currentとprevious→currentの元E/H比較を
専用回復核で再計算する。継承したID集合内で全評価が一致するまで回復周波数はnull。
報告には元二点比較をそのまま残し、回復後のeffective IDを後続継承へ使う。
真の円doubletや上位guard停止を過去anchorで救済しない。

所有先は `history.json`、`sources.json`、`history-results.json`、`manifest.json` と
順序付き `step-0000/` 等で、各stepは二点比較の全ファイルを保つ。
manifestは `superfish_ng_owned_planar_curved_tracking_history` / `saved_version=1`。
`read_owned_planar_curved_history` は全元native、連鎖、回復、報告全体を再計算する。
各stepのコピー前後・全stepコピー後・完了時に全元step hashを検査する。

`recover_owned_planar_curved_history(history,recovery,new_directory)` は、最後の元二点が
subspace PASS/個別未確定で未回復の場合に、新所有先で回復する。
`extend_owned_planar_curved_history(history,next_pair,new_directory,recovery=None)` は
PASSかつmax_steps未満の場合に限り新所有先を作る。元historyは変更しない。
max_steps到達やUNVERIFIEDでは保存先作成前に拒否する。
離散snapshot間の対応であり、連続pathでのidentity、連続体誤差、表面peakの保証ではない。

## 検証と失敗の保全

rawは未使用の `out/p09-planar-curved-history-20261007/` に保存した。
最初のAPI不在は `pair-baseline.log` / `history-baseline.log` のModuleNotFoundErrorで確認した。
独立不変量は回転楕円TEの元節点反射parityで、aはodd/even、bはeven/odd。
元係数を変えず相対内積の偶奇を1e-10で検査し、実rank交換のIDと照合する。
元五nativeの全byte一致は全12場・全RF・係数/規格化も保つ検査である。

初回二点1件3.271秒、履歴1件36.186秒、二点安全3件11.262秒、履歴安全5件91.592秒はPASS。
それぞれ `initial-pair-test.log`、`initial-history-test.log`、`pair-safety-test.log`、
`history-safety-test.log`。native/完了jobの元byte、移動、回復→延長、
新owner回復/元history不変、max_steps、誤anchor/断絶/ID置換、真縮退/guard、
strict/再hash報告改変拒否と独立parityを分けて検証した。

先のoperandを後のコピー中に変える反例で、二点/履歴両方の完了時検出漏れを修正した。
初回試験は相対rootと絶対srcの比較誤りで変異が未発火だったため、
`copy-before-test.log` / `copy-after-test.log` を科学的な再現証拠として数えない。
条件をresolveした未修正源では実変異を伴う2FAIL、`copy-real-before-test.log` 8.211秒。
未修正源は `before-copy-stability-fix/` に保持した。
修正版の同じ2件は `copy-real-after-test.log` 8.128秒PASSで、発火と拒否を確認する。
物理gate・数値kernelは変更していない。

修正後の通常二点/claimなしimport済みjob/全回復履歴・移動再生は
`final-positive-test.log` 3件44.114秒PASS、関連旧履歴・旧所有二点・曲線回復核は
`related-test.log` 10件41.362秒PASS。全実行handleは実終端で生存処理/製品source固定なし。
具体的な終端結果、元412製品/全123カード不変、全源/log/hashと所有byteの最終監査は
`history-acceptance.json` に記録する。新6二点＋7履歴の13種類を分割受入し、一括suite成功とは扱わない。

最終監査は終了0/PASSで、元412製品の全byteと全123カード/依存/文書anchor不変、
9所有履歴/内包分を含む23二点の全hash・元五/八/九byte・creator/claimを確認した。
実変異の未修正版入力とコピーbyteが異なること、修正版拒否先のmanifest不在も確認する。
作成実装は、初回二点時の413源と履歴追加後の414源を区別し、旧412と新二源のarchiveへ束縛する。
最初の監査器が全作成時を414源と仮定したエラーは `initial-audit-error.log` に保持した。
実行中の自分のlogは未完了hashなので最終artifact集合から除き、
先の監査報告/logも `history-acceptance-first.json` / `final-audit-first.log` に保持した。
再監査はbyte/台帳だけで、新FEM求解/物理再構築0。最終記録は `final-audit.log`。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v <selected cases>
```

新caseは `test_planar_curved_tracking_saved` / `test_planar_curved_tracking_history`。
各logに対応する新規raw rootを `SUPERFISH_CURVED_TUNING_TEST_ROOT` へ指定した。
関連は `test_planar_tracking_history` 全5、
`test_planar_tracking_jobs.PlanarTrackingJobTests.test_portable_copied_native_replay_and_completed_reentry` と
`test_planar_curved_identity_recovery` 全4。
最終byte監査で新FEM求解/物理再構築を追加しない。

物理非依存の既存ID集合helperとhash/copy/writeを使い、全物理は専用曲線kernelへ接続した。
新製品は二点所有層と履歴層の二モジュール。新外部資料/依存/legacy参照なし。
full/seed/CLI-worker/GUIは今回未実行。合成円/楕円を測定構造とは扱わない。
