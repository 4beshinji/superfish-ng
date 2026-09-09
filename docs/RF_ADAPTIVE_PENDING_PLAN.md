# RF適応実行中の次計画の共有

2026-09-09。版5では、一様確認の組立末尾にRF選択と次の局所計画を導出していたが、
局所solve後の組立先頭で同じ親・確認場から再度導出していた。
実3イベント検査でRF指標の呼出しが2回になることを先に確認した。

`_VerifiedRFPrefix`は検証済みprefixとともに一つの次計画を保持する。
利用前に既存のprefix検証で実装hash、request、祖先run列、native全snapshotを再照合する。
計画は実行中だけ共有し、永続checkpointから読み込まない。
採用/未採用、RF指標、要素選択、幾何、追跡、積分、表面、停止の定義は変更しない。
計画を使っても、実際に保存された新しいCase/mesh/二次写像と計画の一致検査は残る。
公開replayはキャッシュなしで全判断を再導出する。返したdecisionの変更は内部の次計画へ伝播しない。

## 検証条件

- 実3イベントでRF指標を1回だけ計算し、元親の要素選択と公開replayの完全一致を確認。
- 同じprefixの再読込では次計画を再評価せず、request/祖先/source/実装変更は先に拒否。
- `fc76e64`の自作版5モジュールを保存し、同じnative場を変更前/変更後で交互に3回処理する。
  各prefixのcheckpoint全体を完全一致で比較し、最終文書は保存済み入力とも一致させる。
  計測はincremental assembleのみであり、新しいsolve・保存を含む総workflow時間ではない。
- 標準回帰とseed周波数/RF差を確認する。許容差は変更しない。

再現:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/validate_rf_pending_plan.py \
  --out out/rf-pending-comparison-20260909 \
  --baseline-module out/rf-pending-baseline-20260909/previous_engine.py \
  --checkpoint /absolute/path/to/hemisphere/checkpoint-005.json \
  --checkpoint /absolute/path/to/prolate/checkpoint-005.json
```

使用した絶対パス・入力hash・旧モジュールhash・対象ソースhashはvalidationに記録する。
初回呼出し回数検査71948は終了1（2 != 1）、変更後65973は6検査25.070秒で終了0。
旧版5との交互測定11865は終了0、`out/rf-pending-comparison-20260909` がPASS。
全prefixと入力最終文書が完全一致、eigshを禁止して実行した。

| 5イベントの例 | RF選択回数 旧→新 | 中央値 旧→新 [秒] | 旧/新 |
|---|---|---|---|
| 電気対称半球 10→40→20→80→320要素 | 2→1 | 5.533→5.127 | 1.079 |
| 合成回転楕円体 80→320→113→452→160要素 | 4→2 | 16.805→14.238 | 1.180 |

旧モジュールは保存したgit blob `fc76e64` とhash完全一致。
標準3145は終了0、`out/validation-rf-pending-20260909` がPASS。
685件中683合格・2 skip、434.058秒。seed9モード19量の周波数差0、RF相対差最大8.882e-16。
最終全対象ソースと標準、独立交互測定のhashが一致。既存ベンチマークの更新なし。
この変更で新しいブラウザー検証を行ったとは扱わない。先行費用表示のChrome検証はfc76e64時点。
別の主作業ツリーで長い非球形計算も継続中であり、専有環境の速度試験ではない。

## 残る費用

saved trackingでのnative再読込、親/子の全履歴再構築、辺検査は残る。
本変更から一般的な効率優位を主張しない。主ツリーで検証中の非球形・両尺度の
完走やRF/表面精度を、この初期5イベント比較から受入済みとはしない。
