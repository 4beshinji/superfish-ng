# 材料調整の所有ID回復と最終細分の操作検証

2026-09-22、H16-c。`test_material_hphi_tuning_recovery_saved`で、専用CLIの検索から所有checkpoint再開、実workerの最終細分、管理器再起動後の再生までをつなぐ。

## 独立物理と所有操作

非真空一様材料epsilon_r=4、mu_r=9の同軸断面で、長さを明示区分アフィン写像により変える。目標は解析TEM周波数c/(12 L)。既存の材料回復検証と同じn=6メッシュ、bounds=[0.8,1.18]、relative_cluster_gap=0.04を使い、成功させるための許容値変更はしない。

CLIは検索3試行を保存し、第三試行の元追跡が未解決ID集合のまま、過去の確認済み元場との比較でTEM IDを回復する。ワーカーはこの完成prefixを所有コピーし、実際に細分した第四試行をsolveする。最終細分の比較親と回復anchorは別に保持する。元検索ディレクトリを移動してから管理器を再起動し、要求・全判断・全prefix・回復anchor・全元native/RFを物理再生する。

全試行で解析周波数とcos(pi*z/L)場の材料質量内積を独立に確認する。元3試行のProject/nativeはbyte一致を要求する。元nativeの保存RFと再計算RFを全量比較し、加速区間を持たないケースの両R/Qはnullと理由を保持する。回復anchorや回復規則を書き換えたcheckpointを拒否し、その検査自体が元ファイルを変えていないことも確認する。

もう一つの検査は、真空軸区間と非真空材料・穴を持つProjectをワーカーで保存し、全材料/領域、表示単位、両R/Qの定義比2を確認する。別ジョブへのnative再importでも全bytesとProjectを保持する。非真空を横切る加速区間と未対応loss_tangent入力は拒否する。この一試行の保存検査を穴付き形状の成功調整と混同しない。

## 記録

`out/h16-material-owned-recovery-20260922/initial.log`は新2件601.458秒PASS/終了0。全handle/worker終端。rawの全Project/native/checkpointと`recovery/accepted.json`、`axis/accepted.json`を保持した。実行中の製品実装変更なし。

検索/最終細分の回復anchorはそれぞれ1/2、回復前の個別IDは両方とも`[null,null]`。最終値0.99でTUNED、粗細周波数差18538.145191073418 Hz、目標/粗細gateを別々に通過した。全4試行は解析TEM周波数相対1e-3と場の材料質量内積0.999を満たす。元検索3試行の18ファイルをコピー先とbyte比較し、最終細分を含む24ファイルは改変拒否検査の前後で不変だった。軸/材料/穴の一試行はPAUSEDで、両R/Qと全native/Project再importを検証した。

今回は検査と文書のみの変更。前工程の保存/履歴/CLI-worker成功証拠を再利用し、無変更の製品数値核について全suite/seedを再実行していない。

```
OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache SUPERFISH_MATERIAL_TUNE_RECOVERY_TEST_OUT=out/h16-material-owned-recovery-20260922 uv run --no-sync --python .venv/bin/python python -m unittest -v test_material_hphi_tuning_recovery_saved
```

既存自作の曲線所有回復検査を材料専用CLI/workerへ接続し、目標と場形状は既存TEM解析式で独立検査する。新外部資料・依存・legacy参照なし。FEM/数値許容値の変更なし。この記録はGUI実クリックや全suite/seed受入を含まない。
