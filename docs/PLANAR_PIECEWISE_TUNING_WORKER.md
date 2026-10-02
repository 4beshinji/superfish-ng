# 区分調整workerの所有入力・停止と再開（P04-b-c）

2026-10-02、基準 `3377030`。対象は調整要求4/checkpoint2の投入時所有、
専用worker、完了検証、停止後保存地点のPython選択。GUIはP04-cで受け入れる。

## 修正前に失敗する不変量

検証済み保存地点から投入されたworkerは、投入完了後に元出力が移動しても
先行試行を再生できなければならない。基準では投入後に元出力を移動すると、
workerが元絶対pathのrequest copyを要求して拒否した。実FEMの初回試行と
遅延起動による再現を `out/p04bc-planar-worker-20261002/baseline-rejection.json`
に保存した（session98556、終了0）。

## 所有・保存契約

- 要求4だけ、投入前の物理再生後に全先行trialをジョブ内 `ancestry/trial-NNN`
  へコピーする。Project/native/RF/判断と元実行metadata/claimの全bytesを保持する。
  元絶対pathは投入envelope内の来歴として不変に保存する。
- queued状態のinput_sha256はenvelopeとancestryのrequest copy/全trialファイルを
  束縛する。workerは起動前と実行後に同じ集合・hashを照合し、コピー欠落・リンク・
  不明entryを拒否する。元所有先には再アクセスしない。
- workerは所有ancestryから新しいexecutionへ全prefixをコピーし、全試行を通常の
  実FEM/native物理再生で検証する。コピーのpathだけを変え、Project/native/hash/
  判断/回復eventを変更しない。新trialの実行来歴はworkerの実装hashへ照合する。
- executionのrequest copy、投入時prefix checkpoint、以後の全checkpointと
  全nativeを完了manifestへ束縛する。結果JSONも相対trial名を保存し、読込は
  `execution`を所有先として宣言する。単独checkpointは同じ階層を所有先とする。
- 完了検証は要求/prefix・実試行・判断・実行予算・所有ファイル集合を照合する。
  最終結果の完全物理再生が検証したprefixは、同じ試行と決定核から再構成して照合し、
  各prefixの場比較を重複再計算しない。
- `read_planar_tune_job_checkpoint(directory, index)` は停止したジョブだけを扱い、
  元要求と先行試行・所有先を照合する。新版では投入時prefix地点も選択できる。
  中止/失敗後の確認済みprefixから別ジョブへ再開し、失敗試行を周波数評価にしない。
- 旧要求1〜3/checkpoint1の参照・manifest集合・worker動作は維持する。

PID/claimは実行来歴であり生存証拠ではない。nativeの全byte一致には保存RFと全配列が
含まれるが、それだけで物理精度を主張しない。RF/元場/最低正スペクトルも既存再生で
別に検査する。

## 条件別検査と分割受入

新 `test_planar_piecewise_tuning_jobs` 5件と直接消費先の
`test_planar_tuning_jobs test_planar_tuning_recovery_jobs test_gui_planar_tuning` を選択した。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
  uv run --no-sync python -m unittest -v test_planar_piecewise_tuning_jobs \
  test_planar_tuning_jobs test_planar_tuning_recovery_jobs test_gui_planar_tuning
```

新条件：queued前後の元移動、worker出力移動、管理器再生成、実中止/保存地点選択/別job、
実最終細分と過去anchor回復、矩形TE10解析cutoffと両周波数gate、初回縮退のnull/再開拒否、
queuedコピー改変、solve失敗prefix、再hash後のprefix/ancestry/request/予算/不明ファイル拒否。

session19594は603.667秒、17件中16PASS、同じ中止テストの本体/cleanupで2ERROR、終了1。
テストが中止済みジョブを移動した後も管理器のprocess辞書に旧pathを残しており、
closeが移動前のjob.jsonを読もうとしてFileNotFoundErrorとなった。移動前に回収済み
processを辞書から除くテスト修正だけを行い、この1件をsession11536で40.054秒PASS、
終了0と確認した。製品srcは両実行で固定、395製品hash不変。
新5/直接消費先12の計17種類の成功は分割証拠であり、一度の全件成功ではない。
初回失敗/再確認ログ、開始hash、終端監査を同じ証拠ディレクトリの
`selected.log` / `cancel-recheck.log` / `implementation-before.json` / `acceptance.json` に保持する。
全worker/ツールsessionは終端。製品の数値/停止処理は変更していない。

## P04-b監査と来歴

子aの[元形状法則/比較](PLANAR_PIECEWISE_SHAPE.md)、子bの
[実調整/所有保存/独立TE・TM](PLANAR_PIECEWISE_TUNING_SAVED.md)の成功証拠を再利用する。
本変更はFEM算術、追跡許容差、形状法則、canonical seed TMを変更しない。
seed/全validate/実ブラウザーは本カードの検査対象ではない。
| P04-bの元条件 | 成立した証拠と範囲 |
| --- | --- |
| 元Projectからの有限多項式形状/区間Jacobian/接触・丸め拒否 | 子aの独立重根・幾何・相似解析検査。法則/再生成実装は本カードで不変 |
| 共通参照上の元TE/TM場/全実点の実FEM | 子a/bの相似・非アフィンTE/TM解析/独立mesh、元K/M/RF再生。本カードの回復workerも実FEM |
| 検索/最終個別IDと明示回復 | 子bの主比較nullと過去anchor回復、本カードの実worker最終回復と親/anchor区別 |
| 目標gate/粗細gateの分離 | 子bの独立gate拒否、本カードの解析TE10と両gate成立 |
| 未確認群を評価しない | 子bの真縮退/guard/anchor拒否、本カードの初回縮退UNVERIFIED・周波数/目標誤差null・再開不可 |
| 全元Project/native/判断/RFの保存と元不変 | 子bの全byte・配列/所有再生、本カードの全trial snapshot一致と元checkpoint byte不変 |
| 元移動後の新出力への完全再生/CLI再開 | 子bの移動後CLI。本カードの起動前元移動・完了worker全体移動・管理器再作成 |
| worker実中止/保存地点選択/別job再開 | 修正済み中止テストPASS。中止済みprocessを回収確認後に登録から外して元を移動。稼働中jobの移動は受入対象外 |
| 失敗prefixとコピー/再hash改変拒否 | 子bのnative/law/親/結果改変、本カードのqueuedコピー改変/実行失敗prefix/prefix/request/ancestry/予算/余分なfile拒否 |
| 旧版互換 | 子a/bの旧要求1〜3、本カードの旧worker/回復worker/GUI直接利用12件PASS |

子a/b/cの全条件をこの表で監査し、開発カードP04-b-cと親P04-bをDONEとする。
GUI要求4の編集/読込・全操作と開発親P04の監査はP04-cで受け入れる。

自作の既存planar所有保存/workerとHphi所有設計を使用した。
旧solver資産の読取/実行、外部資料/依存の追加はない。
これは開発カードP04-bの監査であり、原互換課題P04（材料）やD02全体の受入ではない。
