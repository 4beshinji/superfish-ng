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
三例の実bridgeは下記終端追記で受入した。timeoutを終端・再起動の根拠にしない。

既存自作P2/元chart/native/Maxwellの数学を再利用する。新外部資料・依存・legacy参照はない。
主sourceの401製品/15validatorは統合前の独立modern source snapshotに別保全済み。


## 三実bridge終端とTM全帯trace補強（2026-10-07）

78620/54876/89737は終了0、157.838/551.566/555.269秒PASS、新FEM0。
楕円TM境界Bと角TE二尺度B5の全元chart/native/K/M/最低帯を新kernelで再構築し、
元係数/周波数の一致・全RF metadata完全一致を確認。RF浮動差最大3.331e−16、
独立energy/壁最大1.288e−11、signed公共場/literal差最大1.343e−16。
前後401製品/使用10validator/全元accepted rawは不変、各全6artifact snapshotと実終端auditを保存。
三旧validatorの全10コードは `source-bridge-validator-before-all-mode-PEC/` に元hash付きで保全した。
旧bridge内の明示TM壁probeはmode0だけだった。共通 `_restore` は元から全modeの拘束係数≠0を拒否しており、
旧受入eig状態の全帯PEC拘束は保持されるが、独立trace probeの範囲を全帯へ補強する。

実TM3帯でmode0を保持しmode1の壁係数だけを変更する独立反例は、旧probeが未拒否でFAIL/0.031秒。
この孤立trace検査用tamperは有効固有対ではない。原logを保持する。
旧三実handleの終端・コード保全後に、32Gauss実壁の公共 `all_fields_at_reference` で全正mode Ez=0を検査へ変更。
同じ一件だけ0.025秒PASS。新bridge unitは先行3＋新1の計4種類を分割確認、他成功を繰り返さない。
元配列保存にはdtypeとtobytes比較も追加し、signed zeroを含むbitwise条件を明示した。
製品401/物理演算/許容値は未変更。独立trace checkerのcoverage補強であり、全RFや再構築の代用ではない。

別 `check_planar_curved_bridge_fields.py` は既に物理受入したbridgeの全source/archive/rawを照合し、
同じnative geometryと元係数上の公共field methodだけで全signed E/H・全mode PEC・配列bytesを追加検査する。
solver state/代数診断を作らず、行列/スペクトル/独立energy・壁積分を再実行しない。
楕円TM補足76506は27.817秒PASS/終了0、新FEM/物理再構築0。全6modeの各実壁32Gauss Ez=0を確認した。
角TE二尺度の補足54225/85631は実検証中。branch401/使用4validatorを両実終端まで固定する。
出力は各元bridge名に `-fields` を付けた同親folder/log。
新源への角TM二尺度bridgeと主source統合は残条件であり、全P07/全goalは未完了。


## 三例のbyte/全帯trace補足終端（2026-10-07）

76506/54225/85631は27.817/149.105/150.160秒PASS/終了0。
三物理bridgeの全accepted raw/sourceとのbindingを保ち、同じ元配列dtype/tobytesをsigned zeroまで照合した。
楕円TMは全6正modeの全実壁32Gauss点でEz厳密zero、全signed公共E/Hも独立literal式と1e−12以下で一致。
角TE二尺度も同じbyte/公共signed場条件を確認。代数diagnosticsやsolver stateは作っていない。
新FEM/行列・スペクトル再生/独立energy・壁積分の再実行は全0。元三物理bridgeの実証拠を再利用する。
前後401製品/使用4validator/全親bridge・元rawは不変、各全6artifact snapshotと実終端auditを保持。
旧bridge validator10コードは元hashで別保全し、TM mode0だった古いprobeの範囲を上書きしない。
cache branchの数値利用handleは全終了しsource固定を解除した。main38783とboundary37232/67404は生存固定。
角TM二尺度と円独立半径.02 TMの全gate、統合予定sourceへの残bridge/主統合/P07全条件監査を継続する。

## 角TM二尺度の実受入とV2 bridge開始（2026-10-07）

元境界B37232/67404は4200.212/4189.588秒PASS/終了0。各新FEM一回、元A/B二解を全物理再構築。
対象三群last-two RF最大0.002367392/A対B0.004554814、f/E/H・全六帯guard・独立積分も元gateでPASS。
401製品/10validator/全旧raw不変、各11artifact snapshotと観測終端auditは
`out/p07-planar-boundary-refinement-20261007/corner-tm-s{1,2}-boundary-*` に保持する。
旧混合B第三群RF0.551492% FAILを消さず、境界細分で受入した別実解と区別する。

V2 bridge16323/8632はcache checkoutで実行中。同じ親out下の
`source-bridge-corner-tm-s{1,2}-boundary/` と同名logを保持する。
元sourceはgeometry/refinement二変更のboundary variant、新sourceは四変更の統合候補kernel。
全元parent/native/K/M/最低帯、係数/周波数dtype+tobytes、全RF metadata/roundoff、
独立energy/壁・signed公共場と全六TM正modeの32Gauss実壁Ez=0を検査する。
新FEM0。cache401製品/使用10validatorを両実終端まで固定する。主38783とP07/全goalは継続中。
