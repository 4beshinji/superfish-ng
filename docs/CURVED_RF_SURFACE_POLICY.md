# RF三量合格時の明示的な表面細分

2026-09-09。版5の任意指定`surface_refinement_policy`を追加した。
`rf_goal`または未指定は従来のR/Q局所選択。
`uniform_when_rf_passes`は、追跡・積分・五量が評価でき、RF三量は合格して表面だけ未達のとき、
一様確認解を次の親へ採用する。確認合格数は0。そこから改めて一様細分を行う。
五量が連続2回合格したときだけTARGETS_METにする。未知指定、表面未評価、積分未確認を
成功へ読み替えない。RF三量も未達なら元親からのRF局所選択を維持する。

GUIに明示選択を追加し、未達の確認を親に採用した場合は「確認未達・次の親として採用」
および合格数0を表示する。旧版では選択を無効にする。旧request未指定の動作は変えない。
例題は`examples/adaptive_refinement/curved_prolate_rf_surface.json`。
合成回転楕円体の初期写像、五量許容差、12回/100,000要素の上限を従来例題から変えていない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/validate_curved_rf_nonsphere.py \
  --out out/rf-surface-nonsphere-initial-20260909 \
  --reference /absolute/path/to/curved-nonsphere-spatial-search-20260909 \
  --surface-policy uniform_when_rf_passes
```

追加一様対照は既存の受入済み自作FEM report（164,481自由度）をhash/文書一致を検査して再利用。
今回その参照場を再solveしたとは扱わない。差は固定二次写像領域上の比較で、絶対RF誤差上界ではない。
主ツリーの従来方針の長時間計算、標準回帰、CLI/ブラウザー/互換比較も並行している。
時間は共有環境での観測値であり、一般速度保証ではない。

## 検証

- 未実装時は未知フィールド拒否で失敗。追加後12983は4検査32.842秒で終了0。
  E/B各々の未達で親採用と合格数0、再開での一様延長、RF未達時の元親局所分岐、
  native replay完全一致、未知指定と評価未確認を検査した。
- CLI70586は終了0、`out/rf-surface-cli-20260909` に2イベントのPAUSED checkpoint。
- 実Chrome17410は終了0、`out/browser-rf-surface-initial-20260909` の19項目PASS、外部要求0。
  方針の明示入力、未達の親採用/合格数0、replayでの方針復元、その親からの一様再開を確認。
  `rf-surface-progress.png`を実表示。GUI80722/PID161243は停止・終了0。
- 未指定の旧文書比較81886は終了0、`out/rf-surface-default-compatibility-20260909`。
  旧自作fc76e64と半球/非球形初期5イベントの全prefix・最終文書が完全一致。
- 最初の非球形89100は終了1、`out/rf-surface-nonsphere-initial-20260909`。
  両尺度6イベントでTARGETS_MET、五量の追加対照差も基準内だったが、初期同一性の検証式が不正だった。
  同一のピーク区間へ最悪区間差を適用し、区間幅を差として数えていた。
  両尺度の初期端点は完全一致・端点差0、誤った判定値は約3.686e-7。
  `initial-interval-diagnosis.json`と失敗結果を保持した。
- 標準99231は終了0、`out/validation-rf-surface-policy-20260909` は689件中687合格・2 skip、
  472.620秒PASS。seed9モード19量の周波数差0、RF相対差最大8.882e-16。
  終了時の全対象source/旧文書比較hashとブラウザー対象hashが一致。
- 標準終了後、比較スクリプトの初期同一性だけを対応端点差へ修正した。
  停止/追加対照の五量比較には最悪区間差を使う。数値コア・GUI・検査は変更していない。
  修正後78250は終了0、`out/rf-surface-nonsphere-accepted-20260909` の両尺度がPASS。
  最終sourceとの一致、標準時点との差が当該スクリプトだけであることをstandard-coverage.jsonに記録。

## 非球形両尺度の結果

両尺度とも80→320（未採用）→113→452（表面未達だが次の親へ採用）→1,808→7,232要素。
連続合格数は0→0→0→0→1→2、6イベント/14,665自由度でTARGETS_MET。
親子Ritz、全高次積分、個別追跡、初期端点一致、独立native解析体積、固定領域体積がPASS。
全イベントの構造/要素数/自由度は両尺度で一致。五量のMaxwell差は最大4.923e-13、体積8倍則の差0。

| 追加一様対照との差の上界 | 尺度1 | 尺度2 | 基準 |
|---|---|---|---|
| 周波数 | 2.959e-9 | 2.959e-9 | 1e-4 |
| 加速器R/Q | 2.699e-5 | 2.699e-5 | .005 |
| G | 1.592e-8 | 1.592e-8 | .005 |
| Epk/Eacc | 4.467e-5 | 4.467e-5 | .01 |
| Bpk/Eacc | 1.721e-5 | 1.721e-5 | .01 |

| 観測時間 [秒] | 尺度1 | 尺度2 |
|---|---|---|
| 今回の全execute（確認・指標・追跡・保存・診断体積を含む） | 104.942 | 105.398 |
| 今回の全solveだけの合計 | 12.224 | 12.249 |
| 既存版4の過去workflow | 937.137 | 939.714 |
| 一様細分の過去の確認到達workflow | 260.710 | 264.515 |

過去の一様確認は41,281自由度、追加参照は164,481自由度。
表の過去測定と今回の測定は同一プロセスの交互試験ではない。一般的な速度比や誤差上界は示さない。

従来R/Qのみの初回12イベントは両尺度LEVEL_LIMITで保存している。
任意の48回拡大実験60815/PID76757は、新方針が元の12回予算で両尺度を完走したためSIGINTで終了130。
中断直前の経過時間観測4,745秒、検証済みcheckpoint27、solve完了ログ28イベント。
尺度2は未計算で、従来方針の完走時間とは扱わない。
主ツリー`out/curved-rf-nonsphere-expanded-20260909/interruption.json`と全native出力を保持。
中断時点まで主ツリーの対象ソースhashは不変だった。

最終native再検証51871は終了0、`out/rf-surface-native-replay-20260909`。
両尺度のcheckpoint-006をeigsh禁止で公開replayし、文書完全一致（91.725/91.673秒）。
再検証・修正後の両尺度測定・最終対象source hashが一致。全関連実行は終了済み。

一般曲線の幾何近似誤差、一般RF/表面精度、一般効率、親N04の受入をこの例題から主張しない。

主ツリーへの統合では検証対象384ファイルの完全一致を確認した。主ツリーだけのeditable-install metadata 6ファイルは統合前から不変。summaryは主ツリーoutへコピーし、source-location.jsonに原本パスとhashを記録した。native出力/絶対パスcheckpointの原本は `/tmp/superfish-rf-cost-worktree-20260909/out` に保持する。
