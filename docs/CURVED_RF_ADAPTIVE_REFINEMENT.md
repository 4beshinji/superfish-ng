# 版5: RF確認分岐を持つ自動適応

2026-09-09。[設計](CURVED_RF_ADAPTIVE_PLAN.md)に沿って、版5のrequest検証・
イベントplanner・実行・保存再開・canonical replayをAPI/CLIへ接続した。
通常入口は `execute_adaptive_refinement` / `replay_adaptive_refinement`。
専用実装は `curved_rf_adaptive_refinement.py`。版4の経路は保持する。

## 入力と実行の意味

requestのキーと五量/積分/幾何/品質の条件は版4と同じで、`schema_version`を5にする。
確認は`uniform_two_steps`必須。未知指定・非対応幾何・不正な予算/許容差を拒否する。
RF選択には[指標API](CURVED_RF_GOAL_INDICATOR.md)の個別追跡条件も適用する。

版5の`max_levels`・`max_new_levels`は**全実solveイベント数**を数える。
初期解だけでなく、不採用の一様確認と局所solveも含む。版4の採用水準数と混同しない。
`level_runs`/`levels`も版5ではイベント順を表し、native出力は`event-NNN`。
既存checkpoint外形を保持しつつ、各行とdecisionへ明示的な親/採用情報を追加した。

- `refinement_kind`: initial / uniform_probe / rf_local。
- `parent_event_index`: そのsolveが細分した元のイベント番号。初期はnull。
- `accepted`: 採用解列へ入るか。未達の確認はfalseで保存される。
- `uniform_confirmations`: 採用列で連続して合格した一様確認数。局所採用で0へ戻る。
- `confirmation_comparison`: 親とのf/RQ/Gおよび連続離散E/Bピーク比区間の判定。
- `selection`: 局所solveを指示したRF指標・元親の選択番号。
- decisionの`accepted_event_indices`は採用解列、`completed_solve_events`は全実solve数。

一様確認が五量を満たさない場合、RF指標は元親と確認から算出し、**元親**から局所細分する。
局所解のID追跡も元親から行う。確認メッシュへ親の要素番号を転用しない。
五量を満たす確認は採用し、採用列で連続2回の一様確認が合格した場合だけTARGETS_METとなる。
代数残差やゼロ優先度で停止成功へ読み替えない。積分未達・ID不明・区間未確認・予算到達を区別する。

## 保存と再開

初回も実solve後に保存場を読み直し、周波数から再構成したλを使って判定を作る。
再開/replayでも同じ経路を通る。前回確認したλ丸め差で初回とreplayの指標が違う問題を避ける。
確認直後で中断した場合、保存済み確認から指標を再検証し、局所solveだけを新規実行する。
親・用途・採用列・選択・停止は元requestと各native場から導出し、保存値を信頼しない。
全イベントsource snapshotを検査し、失敗時は直前checkpointと未完了runの情報を保持する。
実行内cacheの再利用でもsource/実装hash確認を省略しない。

CLI例（`request.json`は版5）:

```
python -m superfish_ng adaptive-refine request.json --out out/rf-first --max-new-levels 2
python -m superfish_ng resume-adaptive-refinement out/rf-first/checkpoint-002.json --out out/rf-next
python -m superfish_ng replay-adaptive-refinement out/rf-next/checkpoint-005.json
```

JobManagerの新規出力検証は版4のlevel-NNNと版5のevent-NNNを分ける。
版4の実ジョブ検査1件がPASS（4.409秒）。版5の実ジョブでも確認までの2イベントから再開し、
元親から局所イベントだけを追加、manifest・採用列・確認出力改変の拒否を確認した。
`out/curved-rf-adaptive-jobs-20260909` はPASS。両JobManagerは終了済み。
[GUIの版5作成・分岐表示・場選択・取消し後再開](GUI_RF_ADAPTIVE.md)も実ブラウザーで確認した。

## 追加検査

追加4検査がPASS（17.948秒）。未実装の版5を拒否する初回失敗ログを保持する。

- strict request、未知キー・不適切確認方式/予算の拒否。
- 初期→確認→元親から局所の実FEM、確認直後の再開で新規solveが1回、局所Caseにmarkedだけが追加される。
- eigshを禁止したreplayの完全一致、親番号/採用状態の改変拒否。
- 五量のそれぞれが未達なら不合格、ピーク区間未確認の拒否。
- 実一様確認1回ではPAUSED、2回でTARGETS_MET。積分未確認なら再開不可の停止。

## 既存許容差でのCLI・独立解析照合

`out/curved-rf-adaptive-initial-20260909` はPASS。
元の版4電気対称半球requestの幾何・全許容差・予算を保持して版番号のみ5へ変更した。
f=1e-4、RQ/G=0.005、E/B比=0.01。max_levels=8は版5では全イベントを数える。
確認直後にCLIを中断して再開し、全checkpointをeigsh禁止で再検証した。

| イベント | 種類 | 親 | 要素数 | 採用 |
|---:|---|---:|---:|---|
| 0 | initial | — | 10 | はい |
| 1 | uniform_probe | 0 | 40 | いいえ |
| 2 | rf_local | 0 | 20 | はい |
| 3 | uniform_probe | 2 | 80 | はい |
| 4 | uniform_probe | 3 | 320 | はい |

5イベントでTARGETS_MET。採用列は0→2→3→4。全親子のRitz減少と高次積分/追跡を確認。
CLI実行は中断・再開合わせて7.682秒（このローカル実行の観測）。

最終半球を鏡映し、独立SphereTM解析解の全球・エネルギー2 Jと照合した。
`out/curved-rf-adaptive-analytic-20260909` の五量相対誤差は、
f=2.504e-5、RQ=5.875e-6、G=2.348e-6、E比=3.913e-4、B比=1.793e-6で全て同じ基準内。
E/Bは離散ピーク区間の両端を検査した。幾何誤差を含む一般誤差上界ではない。

非球形・両尺度・総費用比較、累積費用の専用表示と長い反復の受入は残る。
新規依存・外部資料・旧資産は参照していない。

## 標準回帰と既存版

標準 `out/validation-curved-rf-adaptive-20260909` は681件中679合格・2 skip、422.318秒でPASS。
seed9モード19量の周波数差0、RF最大相対差8.882e-16。
独立CLIと標準の全対象hashは一致し、標準終了時の全対象hashも確認した。
その後JobManagerの出力名検証2行だけを追加し、版4/版5の実ジョブで確認した。
数値・CLI・全検査は標準時点から不変、最終ジョブ検証は最終全対象hashと一致する。
このインターフェース修正後に全件回帰を再実行したとは記録しない。

版4の既存電気対称半球7水準checkpointは、固有値再計算を禁止して文書完全一致を確認。
`out/curved-rf-adaptive-v4-replay-20260909` はPASS。
