# 平面曲線調整の所有保存と移動再生

P09の所有保存leaf。先行は[実FEM調整・両gate・完全native再生](PLANAR_CURVED_TUNING.md)。
P09/全123カードgoalは未完了。CLI-worker/取消し・独立追跡履歴/実GUIは後続の必須範囲。

`planar_curved_tuning_saved.py` の公開入口は次の四つ。

- `execute_owned_planar_curved_tune(request, new_directory, max_new_trials=None, checkpoint=None)`：
  元要求から実FEM試行を生成するか、完了prefixを新しい所有出力へコピーして実試行を継続する。
- `import_owned_planar_curved_tune(checkpoint, new_directory)`：
  元raw/所有checkpointの全物理再生後、全nativeをbyteでコピーする。新trialの固有場を生成しない。
- `replay_owned_planar_curved_tune(document, base_directory=None)`：全元nativeから結果全体を再構築する。
- `read_owned_planar_curved_tune(path, base_directory=None)`：portable相対pathを明示ownerへ解決して完全再生する。

format `superfish_ng_owned_planar_curved_tune_checkpoint`、schema_version 1。
要求は元曲線調整schema1/完全版3 Projectのまま保存する。SI/per-length/peak-phasor規約、
固定U′/σ、元E/H、全六節点/PEC、全RF/N/A理由を変更しない。
既存直線保存APIのうち物理非依存のpath/byte snapshot/copy/write helperだけを再利用する。
FEM・場・追跡/回復・試行生成/決定は専用曲線調整APIを使い、直線solverへ変換しない。

## 完全prefixと移動

各trialは元Project、job completion metadata、worker.claim、五native（Case/mesh/fields/results/manifest）の
九ファイルを所有する。全entryをregular file/directoryとし、余分なentry/全symlink componentを拒否する。
コピーは元job/claim/implementation provenanceをそのまま保持する。受け取り先が求解したと主張しない。
所有checkpointの全九hashに加え、元物理replay内部は従来八hashを保持する。
request.jsonの完全元要求をcheckpointと照合し、前後のrequest/native/実装不変を確認する。

メモリの戻り値はcanonical絶対path、on-disk checkpointは `trial-001` からの順序付き相対名だけ。
全trialは明示ownerの直下にある必要がある。traversal、末尾slash、別owner、異なる順序を拒否する。
zero-trial checkpointの再生には明示owner/request.jsonを必須とする。
raw prefixは以前の再開で複数directoryにまたがり得るため、取込時は各元trialのcanonical絶対名・順序を確認する。
rawを暗黙のowned再開入力とせず、専用importで全prefixを複製する。

全公開replayは、各要求試行の全二次写像/chart、元Projectと実正帯、全場/RF、E/H追跡、
過去anchor束縛/回復、選択周波数と両gateを再構築する。保存trial/決定を正解として使わない。
所有先を移しても同じ過去trial indexの実native/IDへanchorを束縛する。
新しい実行の内部だけは直前に全物理検証したimmutable元場を再利用する。
コピー前後の元全九hashとコピー先全九hashが一致してから、既検証場の状態を新ownerへ渡す。
各appendで全先行九hash、元要求copyと実装hashを再検査する。公開replayはこのcacheを使わない。

## 失敗と再開

新試行の前に完全prefixのcheckpointを保存する。初回にも `checkpoint-000.json` がある。
新試行が失敗した場合はfailure記録を別に残し、先行prefix/元所有出力を変更しない。
failureには周波数評価を置かず、試行名と先行相対名を保存する。
PAUSEDからだけ新ownerへ再開できる。曖昧/guard未確認・terminal結果を再開しない。
実取消しのプロセス操作は後続worker層で確認する。

## 限定検査・来歴

API未実装のModuleNotFoundErrorを `out/p09-planar-curved-owned-tuning-20261007/baseline.log` に保存した。
独立不変量は実元TM円のf尺度比1.4、元九byte不変と所有相対pathだけでの移動再生。
最初の1件12.691秒PASS（`initial-test.log` / `initial-acceptance/`）。
初回/途中失敗prefix、別owner再開、claim/要求/報告改変・strict path、複数directoryのraw取込、
true TE doubletのnull/terminal拒否の新4件53.052秒PASS（`safety-test.log` / `safety-acceptance/`）。

再hashされた1.01倍coefficientsはf/固有空間を保ってもU′を1.0201倍にするため、
元規格化で拒否する。再束縛したproper shape lawも元native Projectとの不一致で拒否する。
単なるhash拒否ではなく、実再生のエラー理由を `rehash-rejection-reasons.log` に保存した。
新1＋関連旧所有helper利用2＋元曲線native binding1、計4件163.279秒PASS
（`rehash-related-test.log` / `rehash-acceptance/`）。

受入済み円TM・回復付き非円形TEの全nativeを新所有先へbyteで取り込み、
所有先移動後に全prefixを公開readで再生する専用1件は865.527秒PASS。
元rawを保持し、新trial求解・元nativeの再保存をせず、最終二gateと過去anchor/実順位を照合する。
保存FEMの行列/最低正帯を再構築する物理検査は実行する。
handle46796は実終端0、log `accepted-case-test.log`、raw `accepted-case-import/`。
観測timeoutでは再実行せず同じhandleを追跡した。実行中は全製品sourceを固定した。
円の四trial、TEの三trial、両gate/元全場・RFを全九byteと完全物理再生で照合し、
TEの最終実順位odd-x/even-xと過去anchor0を保持した。

新7種類＋関連3種類を分割受入。10件一括のsuite成功や全P09受入と表現しない。
大きい専用1件はdefault unittestで無条件に成功へ数えず、元受入native rootを要求する。
全source/台帳の前監査は `source-card-preflight.json`、終端後の最終監査は `owned-acceptance.json`。
基準401208aの元411製品が完全byte不変、全123カード台帳/依存/文書anchorが不変、
両元受入prefixと移動所有prefixの全九hash、決定/全ID/過去anchorと全log/sourceを照合した。
最終監査は既に終端した成功の物理証拠を再利用し、新trial求解/物理再構築とも0。
51684/61711/12626/10261/46796と最終監査11391は全実終端。生存処理/製品source固定なし。

実行prefixは既存lock環境の次を使用した。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v <selected cases>
```

新7種類は `tests/test_planar_curved_tuning_saved.py` の各caseを上記logごとに選択した。
関連は `test_planar_piecewise_tuning.PlanarPiecewiseTuningTests` の
`test_owned_path_names_links_budget_and_request_binding_are_strict` / `test_failed_new_trial_keeps_owned_prefix_and_original_immutable` と
`test_planar_curved_tuning.PlanarCurvedTuningTests.test_valid_native_still_requires_the_regenerated_trial_project`。
`SUPERFISH_CURVED_TUNING_TEST_ROOT` で各logに対応する未使用raw保存rootを指定し、
大きい専用caseでは `SUPERFISH_CURVED_OWNED_ACCEPTED_ROOT` に
`out/p09-planar-curved-tuning-20261007` を指定した。元rawを再求解/改変しない。

新外部資料/依存/legacy参照なし。新製品は所有層1モジュールのみ。
元曲線/共有/seedの科学kernelを変更しない。full/seed/CLI-worker/GUIは今回未実行。
円/楕円は合成例で測定構造ではない。P09と原互換要件を含む全123カードgoalは継続する。
