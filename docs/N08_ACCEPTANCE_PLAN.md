# N08：公開適応・保存・GUIと親N04の受入監査

2026-10-08 JST、N08 **IN_PROGRESS**。先行N07は `a860099` で受入済み。
原123カードは75 DONE/3 IN_PROGRESS（H17/C07-planar/N08）/45 PLANNED。
対象は[原N08](development-plan/05-accuracy.md#n08)と、既存の[N04受入表・残件四群](N04_ACCEPTANCE.md)。
既存文書を保存し、完了した数値例だけへ親課題の条件を狭めない。

## 原条件と必要な証拠

| 条件 | 今回の照合と納品 |
|---|---|
| 対象量の精度・費用・全域確認 | N05三形状/量別目標、N06固定12行、N07前後全場一致と実測を再hashして再利用。公開エンジンの元選択・停止と六adaptive保存系列を再構築して照合する |
| 保存/再開/GUIの一致 | 公開 `_assemble` でnativeから元形式のcheckpointを作り、公開reader/replayで全履歴を再検証。N07の共有を公開保存/再開へ広げない。現行関連源と既存実worker/GUI証拠を束縛し、変わった操作または証拠が弱い部分だけ追加確認する |
| 上限未達表示、実中止再開 | N03受入済み全検証の該当unitの実assertion・PASS log・現行依存源を確認する。Job completeと数値達成を分離し、生存していたworker中止・完成checkpoint保持・新job再開の証拠を確認する |
| 旧履歴・選択移送・大規模表示 | N04受入表の四群、固定/混在履歴・選択移送・250000要素表示・実native/ブラウザーの既存証拠と現行源を照合する |
| 改善/悪化範囲と親の採否 | 円筒/丸めで一様が有利、今回の球で適応が有利、旧球の適応非優位、円筒費用/RSS微増、N07共有の専用診断scopeを明記する。四群に未達が残れば親N04を閉じず、具体的な残件と次工程を記録する |

元Case/source/全mode/実ID、SI/peak phasor/U、両R/Q、元数値閾値・資源を維持する。
有限参照格子・固定P2領域の経験的結果を連続問題の誤差上界と呼ばない。
一般再メッシュ等の既存残件を文言の変更だけで除外しない。

## 選択した検査と実行境界

着手時に全suite/FEMを再実行しない。
N03の1405対象源で実行された `test_adaptive_refinement_jobs`、`test_gui_adaptive_refinement`、
`test_curved_adaptive_refinement` と関連元adaptive/saved/marked/history系の結果を、
実log・実assertion・現行関連依存のbyte一致が成立する範囲だけ再利用する。
現在の公開adaptive/curved/job/GUI moduleと三testは、このN03源とbyte一致している。
source追加後の新1432対象全suiteが実行済みという扱いにはしない。

新しい公開保存経路の照合は、N07の六adaptive系列の全nativeを使用する。
元assembler/readerをそのまま呼び、固有値solve/eigshは禁止して、新FEM0で再構築する。
参照付き専用workerの余分な診断metadataを公開checkpointへ転写せず、公開engine自身の出力を照合する。
保存先は未使用 `out/n08-public-acceptance-20261008`。元N06/N07 native/入力/結果は書き換えない。
実行中はsrc/tests/scripts/examplesの1432対象源を固定する。

新外部資料・依存・legacy参照はなし。数値核・選択・停止の変更は予定しておらず、
不一致があれば元失敗を保持して原因を限定する。文書/監査だけの完了記載のためにFEMやfullを増やさない。
公開保存照合・操作/既存証拠・四群照合の終端前にはN08も親N04もDONEへ進めない。
