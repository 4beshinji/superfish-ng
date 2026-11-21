# RF版5：中断した固定測定の保存と集計

2026-10-14 JST、`ADD-N04-rf-goal-05` **IN_PROGRESS**。
固定36測定はユーザーによるgoal解除で停止した。今回は中断後集計までを区切りとし、
測定の自動継続は行っていない。05/06/親N04/全実装計画の完了ではない。

## 今回の範囲と受入条件

元 `out/n04-rf-goal-fixed36-20261014/` を読み取り専用で扱い、別の新規出力へ
公開済みの連続prefixを回収する。元計画・束縛SHA・source端点・費用算術・実採用祖先の
判定が一致し、未公開行と未実行行を明示できることを今回の受入条件とした。
checkpointの確認達成を終端費用の記録へ昇格しない。

`scripts/recover_curved_rf_goal_measurements.py` を追加した。
明示的なgoal解除の停止receiptをSHA指定で受け取り、固定36計画と公開行の順序を照合する。
行/bundle/journalの束縛、各終端行の元source前後一致、fresh/非再開/非開発、
nativeの元行ディレクトリを検査し、既存readerでnative/sampleの全byte SHAを確認する。
費用と実採用祖先の判定を再計算し、両反復の比較と全量別誤差CSVを出力する。
入力を出版直前にも再hashし、元出力内と既存の出力先への書込みを拒否する。

測定時のsource端点と、集計時の現行source差分は別欄に保存する。
今回は集計script/testの二源追加だけで、測定時に存在したsourceは全て不変だった。
未公開32行目の終端費用と全測定の最終source端点は **UNKNOWN** のまま保持する。
停止receiptは既存の操作証拠であり、この集計がprocessの生存確認を実施したとは扱わない。

## 保存された結果

元測定commitは `e041f3c674a672d9d9c11bb41f80f6f643946f47`。
CPU/BLAS1、固定予算・順序・初期nativeを使用し、終端31行のsource端点は全てUNCHANGED。
31行/161 eventのうち独立CONFIRMEDは27行、残る4行は長球 `rf_goal` のLEVEL_LIMITである。

| ケース | 終端行 | CONFIRMED | 保存event |
| --- | ---: | ---: | ---: |
| 球 scale 1 | 6 | 6 | 24 |
| 球 scale 2 | 6 | 6 | 24 |
| 長球 scale 1 | 6 | 4 | 46 |
| 長球 scale 2 | 6 | 4 | 46 |
| 丸め二葉 scale 1 | 6 | 6 | 18 |
| 丸め二葉 scale 2 | 1 | 1 | 3 |

32行目 `rounded-two-lobe-scale-2-repetition-1-rf_goal` は3 native eventと
TARGETS_MET/CONFIRMEDのcheckpointを保持するが、終端manifestとprocess費用がないため
未集計のままとした。33〜36行目は未実行。監視を停止した後、測定sessionの終了130と
元コマンド/出力先に一致するhost processが0件であることを既存停止receiptへ保存した。

長球rf_goalは両尺度/両反復とも12 eventで止まり、採用列は0/2/4/6/8/10、
最終採用行の両R/QとEpk/Eaccが独立gateを満たしていない。
最初の精度達成は棄却probe 3であり、方式の成功比はnullのまま保持した。
`uniform_when_rf_passes` は6 eventで確認達成する。
そのnative pathの一様/方式比は1.883〜2.062だが、全processの比は0.777〜0.891である。
丸め二葉scale 1でも全processの一様/rf_goal比は0.513/0.517だった。
これらの有限測定では一様の全processが速く、一般的な優位は主張しない。

既存の軽量metadata監査では、長球の同方式反復が同じRF/判定を保持し、
同じ履歴のMaxwell scalar尺度則の最大相対差は長球2.120e-12、
丸め二葉の一様rep 1は4.048e-13だった（規約/全native mode数を保持）。
これは全E/H・軸場の尺度則や係数からの全場再構築の受入ではない。
方式間のquadrature診断はscopeが異なるため、辞書全体の一致を要求しない。
診断scopeと実native mode数に対する初回検査の誤った仮定は元ERROR receiptで保持し、
結果や閾値の変更は行っていない。

## 検証と証拠

最終集計は `out/n04-rf-goal-interrupted-recovery-final-20261014/`。
全2,013束縛ファイル（native/sampleの483 NPZを含む）を照合し、
161 event × 両Gauss次数 × 九量 = 2,898 CSV行を保存した。新FEM/固有求解は0。
全native/sampleのSHA照合は行ったが、係数からの場再構築と独立参照の再計算は未実施である。

- 最終 `summary.json` SHA256: `4e64e71b54a264f5e9f902977d68bbc43d6bc0134aeac5f87a2d1eb9f458e8a4`
- `errors-vs-dofs-and-time.csv` SHA256: `440ebb01e15860bec5bf5a48b4ae4d5315f96d54eab532ac9f9b4fec234a2ca8`
- 停止receipt SHA256: `8fa4a0883961c578bc134ec9e6eb26e5c294e5ba24adb8a15b4c8630c20e90c1`

新recovery 4 unitは3.324秒PASS。未公開CONFIRMED checkpointを成功へ数えないこと、
改変された費用/判定とSHA、行/試行の欠落、stop不一致、source変更、別行の束縛、
固定計画の変更、元出力への書込みと上書きの拒否を確認した。fixtureの元全byteも不変。
直接consumerの既存runner 5 unitは7.922秒、summary 6 unitは0.033秒PASS。
計15件の対象unitは全て新FEM0。数値核/計画/予算/閾値に変更はなく、seed/fullは対象外。
最後に `..` を含む出力パスも元測定内への書込みとして拒否するguardを加え、
recovery 4件だけを再確認した（`recovery-output-path-tests.log`、PASS）。

初回集計の説明がreaderのSHA照合範囲を過少記載していたため、説明と束縛一覧を修正し、
最終版を別の新規outへ保存した。初回outは保全し、最終証拠に混ぜていない。
新依存/外部資料/legacyを集計へ使用していない。Hosted CI/GUIは今回未実施。

```sh
UV_CACHE_DIR=/tmp/superfish-uv-cache OPENBLAS_NUM_THREADS=1 \
uv run --no-project --python .venv/bin/python python scripts/recover_curved_rf_goal_measurements.py \
  --measurements out/n04-rf-goal-fixed36-20261014 \
  --stop-receipt out/n04-rf-goal-fixed-runner-20261014/stopped-after-goal-cleared-20261014T033150Z.json \
  --stop-receipt-sha256 8fa4a0883961c578bc134ec9e6eb26e5c294e5ba24adb8a15b4c8630c20e90c1 \
  --out out/n04-rf-goal-interrupted-recovery-final-20261014
```

上記outは既に存在するため、再検査時は別の新規outを指定する。
05の残件は全36行の終端結果・両反復/全場の尺度則と費用/図の監査、
06は全保存場再構築と実GUI操作、親N04は原条件監査である。
元32行目の再開を無中断の固定36へ混ぜない。固定36の受入を再開する場合は
[固定runner](CURVED_RF_GOAL_EFFICIENCY_FIXED_RUNNER.md)のsourceを固定して新outへ一式を実行する。
