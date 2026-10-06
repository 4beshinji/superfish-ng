# P08：曲線nativeの保存と物理再生

2026-10-07。P08の最初の有界変更。P07の受入kernelは変更せず、専用
`planar_curved_saved`を追加した。P08はIN_PROGRESSであり、Project/共通dispatch、
CLI-worker、Study、元場表示と実GUI操作は続く必須範囲である。

## 契約と実装

`save_planar_curved_run` / `read_planar_curved_run` / `planar_curved_result`は
`PlanarCurvedCase` / `PlanarCurvedSolution`の専用API。schema_version 3を用いる。
旧版1/2の専用読取は維持した。最初のこの段階では共通入口から版3を受け付けず、
続く[共通操作経路](PLANAR_CURVED_OPERATIONS.md)で版3へ明示dispatchを追加した。
保存形式は`case.json`、`mesh.npz`、`fields.npz`、`results.json`、最後に公開する
`manifest.json`の五ファイル。新規出力だけを作り、既存ディレクトリを上書きしない。

元の全二次node、六node cell、三node境界と境界owner/local edge/free DOFを保存する。
係数と周波数はfloat64の元配列を保持する。読取では同じ全Domainから実K/M/freeを
再構築し、残差・単位長energy正規化・直交性・全TM PEC拘束・TE定数核排除と
要求した最低正モード帯を検証する。係数の再正規化、固有ベクトルへの置換は行わない。
全メッシュ配列と係数/周波数はdtype・shape・bytesで照合し、符号付きzeroも保持する。

全モードのenergy、実曲線壁の損失、Q/G、面積/周長、求積次数、phasorとJ/m・W/mの
metadataを再生成して保存結果と照合する。二つのR/Q・Vacc・Eaccの理由付きnullも対象。
ハッシュ一致だけを物理検証とせず、ハッシュを付け直した改変を拒否する。
通常ファイル・五ファイルの完成条件・途中変更の前後snapshotも検査する。
元配列の保持は離散化誤差の証拠ではなく、P07の独立物理受入を継承するための保存契約である。

## 反例と限定検査

先に実曲線TE/TM各四モードを解いた`test_full_physical_roundtrip`を実行し、
専用native API未実装のModuleNotFoundErrorを再現した。数値不変量の破綻ではなく、
要求する保存機能が存在しないことの再現である。
元logは`out/p08-planar-curved-native-20261007/native-baseline.log`に保持する。

実装後は新7件と旧版1/2直接利用5件、計12件を一回実行し、終了0/1.684秒PASS。
全配列・全12 signed E/H成分・全RF/metadataの一致、TM拘束zeroの負符号保持、
有効な曲線平行移動/メッシュ不一致・RF/理由/版の再hash改変、倍振幅・PEC破壊・周波数改変、
残差と正規化を満たす上位三モードだけの偽最低帯、float32変換、検証途中変更、
未完成/余分ファイル/リンク/破損/重複NPZを検査した。不正解の保存は出力作成前に拒否する。
旧版1/2の保存再生と旧物理改変/帯/途中変更検査もPASS。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest \
  test_planar_curved_saved \
  test_planar_polygon.PlanarPolygonTests.test_native_v1_and_v2_replay \
  test_planar_polygon.PlanarPolygonTests.test_rehashed_case_and_version_tampering \
  test_planar_polygon.PlanarPolygonTests.test_source_changes_during_v2_replay \
  test_planar_rf.PlanarRFTests.test_native_physics_replay_rejects_rehashed_corruption \
  test_planar_rf.PlanarRFTests.test_native_does_not_accept_a_valid_but_wrong_frequency_band
```

成功logは`out/p08-planar-curved-native-20261007/native-selected-tests.log`。
専用保存層のみの追加で、既存曲線/共有P2/seed TMの数式・solve・依存は変更していない。
追加の専用validator/full validate/seed/実GUI/CIは実施していない。
既存五ファイルIOと厳密parser、曲線solverの物理再構築を再利用する独自実装であり、
新外部資料・依存・legacy参照はない。

P08全受入には[接続計画](PLANAR_CURVED_INTEGRATION_PLAN.md)の残る直接利用先と
実中止/再起動・旧版操作が必要。P09と原要件を含む全123カードgoalは継続する。
