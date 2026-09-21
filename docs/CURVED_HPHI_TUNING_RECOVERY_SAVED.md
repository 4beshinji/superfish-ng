# 曲線調整回復の所有操作とH13-d監査

2026-09-22。H13-dの条件別監査を受入済み。数値実装を変更せず、実曲線調整の検索時/最終細分の回復eventをCLI・worker・所有保存へ通す。全goal/親H13は未完了。

## 検査内容

`test_curved_hphi_tuning_recovery_saved`を追加。回復ケースはH13-cで物理受入済みのshear=1/64、bounds=[0.8,1.12]、通常cluster幅0.06、既定anchor controlsを使用。独立に元曲線FEMを解き、写像された近似TEM cos場との質量overlap>.999で目標モードを定める。直線式を曲線の厳密周波数としない。要求・独立目標nativeも証拠出力へ保存する。

CLIで検索3試行を保存し、検索時回復PASSのPAUSEDから別workerで最終細分へ再開する。完了後に元検索出力を移動し、管理器を再生成してworkerの要求・全checkpoint・全native・回復eventを再検証する。検索/最終のanchor index [1,2]、コピー済みprefix byte、各元場のTEM状overlap、元RF全量、回復event改変拒否、全所有ファイル不変を確認する。worker検証は結果を返す専用verifierを一度呼び、同じ管理器状態の全数値再生を不用意に重複しない。

別ケースでは曲線の穴付きProjectをworkerで1試行保存し、全Project、穴、元native/全RFの保持を検証する。このPAUSED結果を穴付き調整成功の証拠とはしない。穴付き非一様調整の実TUNED/粗細差は[H13-c監査](CURVED_HPHI_TUNING.md)の別受入。

## 実行記録

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache SUPERFISH_CURVED_TUNE_RECOVERY_TEST_OUT=out/h13-curved-tune-recovery-owned-20260922/artifacts uv run --no-sync --python .venv/bin/python python -m unittest -v test_curved_hphi_tuning_recovery_saved
```

stdout/stderrは同じ親出力の`acceptance.log`。session33752は2件PASS、1448.786秒、終了0。各ケースは未使用の`artifacts/recovery`/`artifacts/hole`を排他的に作る。成功時だけ各`accepted.json`を保存する。両accepted.jsonを確認した。srcは全検査中に固定し、途中待機で重複起動していない。

## H13-d条件別監査（受入済み）

| H13-dの条件 | 証拠/現在の状態 |
|---|---|
| 全元native/Projectを所有 | [調整API](CURVED_HPHI_TUNING_SAVED.md)、[追跡pair](CURVED_HPHI_TRACKING_SAVED.md)。穴付き/回復調整の操作追加2件もPASS |
| 追跡・回復履歴を所有して再生 | [曲線履歴](CURVED_HPHI_HISTORY.md)：新履歴3件、anchor native hash、回復後継承・全祖先保持、未確認停止を受入済み。調整回復の所有再開・最終細分TUNEDも確認済み |
| CLI/worker接続 | 調整専用3CLI、追跡/履歴専用5CLI、専用workerと履歴延長を受入済み。本検査で調整回復の検索→worker最終細分を確認済み |
| 中止/再開/管理器再起動 | [調整worker](CURVED_HPHI_TUNING_WORKER.md)と追跡pair/曲線履歴で実プロセスと新管理器を確認済み。回復調整の再起動も確認済み |
| 改変拒否 | 既存専用検査でnative bytes、ID、要求、再hash summary、初期checkpoint欠落、symlinkを拒否。調整回復event/要求改変も拒否を確認済み |
| 元出力移動後の再生 | 所有調整/pair/historyの受入済み証拠。回復調整のprefix元出力移動後も確認済み |
| 旧保存要求の互換 | 各接続の旧直線保存・worker・履歴・非一様CLI回帰を分割検証済み。数値/保存契約は不変、全suite/seedを実施したとはしない |

全行の証拠と全handle終端を確認し、H13-dを受入とする。H13-eは実GUI/APIの全native/RF一致と親H13監査で、別途未完了。

## 来歴

既存自作のH13-c実曲線fixtureとH13-d所有検証APIを接続した受入試験。追加外部資料・依存・legacy参照なし。FEM/形状/求積/物理許容差に変更なし。

途中観測：worker `20260922-014123-287633c4a5`は4試行TUNED、検索/最終回復PASS、粗細差558674.2841963768 Hzを保存。この時点では受入保留とした。その後、親テストの全prefix/回復再検証・改変拒否、穴付き所有ケースも成功し、全handle終端と両accepted.jsonを確認した。


## 最終照合

`final-audit.json`で367実装ファイルのhashが両workerの実行記録と現在のsrcに一致し、所有30ファイル（回復4試行）/12ファイル（穴付き1試行）のmanifest hashが全て一致することを照合した。回復例はTUNED、穴付き所有例はPAUSED。この検査のために数値ソースは変更していない。既存各段階の成功ログも再確認し、CLI/worker/履歴の一般受入と今回の回復/穴付き所有の追加受入を組み合わせた。

H13-dで確認したのは所有保存とCLI/worker操作まで。H13-eの実GUI、APIとの全native/RF一致、親H13の最終監査は未完了。H14の材料界面比較仕様は待機中に文書だけで独立受入したが、材料比較H15/H16は未実装である。
