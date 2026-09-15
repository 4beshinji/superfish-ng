# 平面RF調整の専用workerと保存再開

2026-09-15 JST、開始HEAD `c473b58`。D02の平面調整をJobManagerの独立プロセスへ接続する。
受入条件は、別PIDでの実FEM、試行上限による保存停止、実中止後のチェックポイント再開、
管理器の再作成、元場の保持、未確認結果と処理完了の分離、改変/不正要求/重複実行の拒否。
API/CLIの[平面調整契約](PLANAR_TUNING.md)と物理閾値は保持する。

`JobManager.start_planar_tune(request, max_new_trials=None, checkpoint=None)`で開始する。
専用kindは`planar_tune`。入力は`planar-tune-request.json`、結果は`planar-tune-results.json`。
試行とチェックポイントは`execution/`へ保存する。通常のstatus/cancel/list/closeを利用できる。
既存の軸対称tune・平面独立Studyと混同しない。専用調整GUIは未接続である。

## 完了・途中保存の検証

投入前に要求と再開元を検証し、不正要求でジョブディレクトリを作らない。
queued時点の入力hashを保持し、実行前/実行後の変更を拒否する。
排他的な`worker.claim`で同じqueued要求を複数workerが消費するのを防ぐ。
このPID記録はプロセスの生存証拠として使用しない。

完了manifestは入力・結果・worker claim・新規試行の全nativeファイル・全チェックポイントを結び付ける。
`read_job(..., verify=True)`は実場を完全再生し、以下を照合する。

- 元checkpointの要求、全既存試行、場hash、個別ID継承が一致する。
- 新規試行の場所と個数が、そのworkerに割り当てた出力先/予算と一致する。
- 新規試行の実装hashがworkerと一致し、取り込んだ別解を新規計算と表示しない。
- 各保存checkpointが、完全再検証した最終履歴の正しいprefixとその時点の停止判断に一致する。
- 状態/manifestのkind、処理結果、再開可否、試行数、入力hash、物理が一致する。
- 状態・manifest・全ファイルが読取開始/終了で一致する。呼び出し元が古い状態を渡した場合も拒否する。

全最終履歴で検証した各場比較はprefixにも共通なので、checkpointごとに全比較を重複実行せず、
検証済み履歴から途中の判定を再構築する。チェックポイントの内容を単にhashで受け入れる方式ではない。
kindを書き換えても専用ファイルの存在から専用検証へ入り、一般ジョブとしての迂回を拒否する。

UNVERIFIED/REFINEMENT_FAILED等は計算処理が完了したジョブとして保存できるが、
`tuning_status`を保持し、`numerical_validation=not_checked`を変えない。
中止や例外後は完了manifestを作らず、完了済みcheckpointから別ジョブへ再開する。
終端結果の再開と完了ディレクトリのworker再実行は拒否する。

## 検証証拠

`test_planar_tuning_jobs`は5種類を分割検証した。
初回6.424秒では4件が、既存平面ソルバーの`worker.claim`を期待ファイル集合に含めていなかったため失敗。
集合へ明示追加し、外側workerにも排他的claimを追加した。
修正後19.969秒では4件PASS、中止再開の1件は目標が数値端点で挟まれずUNBRACKETEDとなった。
物理閾値を変更せず、その試験の目標を幅0.21 mの独立解析周波数へ変更し、同1件を2.200秒でPASS。
別途、呼び出し元の古いstateが受理されることを専用保存ジョブで再現し、実ファイルとの一致検査を追加した。
改変拒否の1件を0.636秒で再検証した。単一の5件一括PASSとは記載しない。

検査内容は、TE実順位交差、別PID、停止再開、管理器再作成、元場改変拒否、実中止、
正方形合流の周波数未評価、無効入力での未作成、再hashされたprefix/予算/kind改変、
投入後入力変更、注入したworker失敗、完了worker再実行拒否である。

直接関連の`test_tuning_jobs`・`test_planar_jobs`・`test_planar_tuning`は25件42.617秒PASS。
共通管理器の`test_jobs`は7件1.226秒PASS。
数値核の変更はなく、full validatorやseedは再実行していない。
今回のread_job変更は専用kind/ファイル名の分岐追加であり、既存経路は上記関連検査で確認した。

専用記録は`out/planar-tuning-worker-20260915/`。
元矩形の幅0.30/0.34 mを初回2試行で停止、管理器を再作成して二分点0.32 mと最終細分を計算。
2ジョブの別プロセスはともに終了0。2回目の管理器再作成後もTUNEDを完全再検証した。
新規4実FEMに加え、manifest不一致診断用の初回1実FEMを別のprobeジョブとして保存した。
probeを成功workerの件数には加えない。unit内の計算も別である。

前回APIの4試行とworkerの4試行は、4組40 NPZ配列・全3モードのRF量が完全一致。
72 native保存ファイルを保持した。前回確認した独立解析周波数/Maxwell尺度則の同じ解を利用しており、
workerが物理量を変えていないことを直接比較した。
最終粗細差は21891.756382226944 Hz、事前指定の目標/粗細200 kHzゲートを両方満たす。

実行中の製品338ファイルSHAは不変。その後のstate照合追加は、同じ2保存ジョブを再計算なしで検証し、
ジョブ全53ファイルを保持、古いstateの拒否も確認した。72と53は重複するので加算しない。
実行時/最終検証時の両hashを[benchmark](../benchmarks/tuning/planar-tuning-worker-20260915.json)に記録した。
全対象プロセスは終端回収済み。新しい資料・旧コード・依存は導入していない。

次は平面調整の専用GUI。Hphi系の調整・一般形状法則・D03等は残り、
親33=10受入/16進行/6他未受入/1範囲外、全計画goalは継続する。
