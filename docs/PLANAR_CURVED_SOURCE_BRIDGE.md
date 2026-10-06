# P07：受入済み元解から統合予定sourceへの物理bridge

2026-10-07、別checkout `p07-reference-basis-cache`。主checkoutの元円独立検証38783と
boundary branchの角TM37232/67404の源を変更せず、受入済み元解を新kernelへ結び付ける。
P07全条件/source統合は未完了。P08/P09と全123カードgoalを維持する。

## 受入と保全

新driver `scripts/validate_planar_curved_source_bridge.py` は新固有解を生成しない。
元accepted report/rawの全terminal snapshot、全旧source前後401、全元validator hashを必須とする。
元主sourceからgeometry/location/refinement/solver四変更・旧397製品不変、
統合予定sourceが既に物理受入したstrict/cache/grouping sourceと完全一致することを確認する。
旧受入sourceのvariantは旧main、geometryだけのBVH、geometry/refinementのboundaryに限定する。
復旧TE B5のrawは元中断先に残るため、その全folder hashをaccepted recovery内のsnapshotへ結び付ける。
元reportのlast-two・独立A/B・完全guard・独立energy/壁を保持し、新sourceの一致を追加証明する。

全元parent chartをFraction ancestryから再生成し、全native/geometry/K/M/最低正帯を物理再構築する。
元係数/周波数をbitwise保存し、全RF schema/metadata/単位・次数・両R/Q/null理由を完全保存する。
数値RF差はcanonical閉壁parameterの浮動丸めだけ、相対1e−12以下を必須とする。
独立energy/実壁積分は元1e−8、元map丸めは512ε/local extent、geometry予算は1e8のまま。
元場は48cell/各3参照点で公共APIの全signed E/Hと独立literal P2/Maxwellを1e−12で比較する。
TMは全実壁の32Gauss点でessential Ezが厳密に0であることも検査する。
小さな代数残差を離散化差へ読み替えず、保存済み実last-two/A/B gateと新source物理検査を別記録する。

## 限定unit

新3件は0.007秒PASS/終了0、`out/p07-planar-exact-reference-20261007/source-bridge-tests.log`。
実patch TE正2帯のRFを用い、float丸め1e−13許可/1e−10・NaN・inf拒否、guard欠落/schema欠落、
peak/単位/次数/両R/Q/null理由改変の拒否、実signed公共場とliteral P2/Maxwellの一致を確認した。
旧solver/strict/groupingの14成功を文書や検証器追加のため繰り返さない。
源変更はvalidator/testのみ、全401製品は既物理受入sourceから不変。full/seed/GUI/hosted CIは未実行。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-reference-basis-cache/src:/tmp/superfish-ng-p07-reference-basis-cache/tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest test_planar_curved_source_bridge
```

## 実再構築中の三例

| 元受入解 | handle | main ignored出力 |
| --- | --- | --- |
| 楕円TM尺度1の境界B | 78620 | `out/p07-planar-exact-reference-20261007/source-bridge-ellipse-tm-s1-boundary/` |
| 角TE尺度1のB5 | 54876 | 同親 `source-bridge-corner-te-s1-B5/` |
| 角TE尺度2の元保存B5 | 89737 | 同親 `source-bridge-corner-te-s2-B5/` |

各同名logを保持、新FEM0。branch全401製品/使用10validatorを上の三実終端まで固定する。
完了FEMを再solveせず、残る角TM二尺度の実受入後にも同じbridge条件を適用する。
現時点で三例の実bridge成功は未確認。timeoutを終端・再起動の根拠にしない。

既存自作P2/元chart/native/Maxwellの数学を再利用する。新外部資料・依存・legacy参照はない。
主sourceの401製品/15validatorは統合前の独立modern source snapshotに別保全済み。
