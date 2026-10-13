# RF版5：固定36実行器と量別費用の集計

2026-10-14 JST、`ADD-N04-rf-goal-05` **IN_PROGRESS**。
04は[条件別監査](CURVED_RF_GOAL_EFFICIENCY_WORKER_ACCEPTANCE.md)でDONE。
本書の実装/対象unitは実36行の数値受入を意味しない。06/親N04/全計画は未完。

`scripts/validate_curved_rf_goal_efficiency.py` は固定計画の全36行だけを、元順序で
別プロセスへ逐次起動する。開発上限、過去native再利用、行の絞り込み、予算拡大は持たない。
既存の04専用CLI/supervisorを使用し、各行に3600秒/32 GiB、BLAS1、CPUのみを適用する。
失敗/資源停止/精度未達を保持して次の行へ進む。source変更では後続を止める。
共有参照検査の前後と全実行前後を監査し、出力先は新規作成する。

`curved_rf_goal_efficiency_summary.py` は元誤差と実親から採用祖先の判定を再計算する。
native TARGETS_METだけでは比較成功にしない。新規・非開発・非再開・process成功と
独立CONFIRMEDが揃う場合だけ確認達成を採用する。
棄却probeの費用も累積し、診断達成、採用初回達成、三祖先確認を別欄で保存する。

費用はroot native path、solve/normalization inclusive、eigenproblem inclusive、
投入からのprefix wall、process全体wall、全event最大DOF、確認DOF、最大RSSを区別する。
solveはassembly/normalizationと観測負荷も含み、eigenproblemはその部分集合である。
同名のnested呼出しを二重加算せず、欠測はnullとする。独立phase別内訳はexclusive和を使う。
各行の元phase treeもbundle/native journalに保存する。
共有準備の既存実測と今回の共有参照検査を別保存し、未記録anchor求解費用はUNKNOWNとする。

行が終了するたびに `row-NNN.json` を排他的に公開する。
集計中の例外でもattempted行・未集計行・未実行行、終端bundle、元例外を区別して保持する。
36行の全費用・二反復の両値/範囲/順序を保存する。方式速度比は一様との両反復が全て
確認達成の場合だけ算出し、未達/資源停止を成功比へ混ぜない。

CSVは全event・両次数・九量の誤差/元gate/実親/採用可否を保持する。
量別科学図は実親の辺だけを接続し、棄却probe→localという架空の連続履歴を描かない。
欠測とzeroを区別し、両反復/両次数と非採用点を表示する。図は精度受入を代行しない。
全保存場の再構築とGUIは06の条件として明示する。

## 実装検証

rawは `out/n04-rf-goal-fixed-runner-20261014/`。
新summary6/runner5＋元metrics9の20個別unitが7.204秒、終了0/PASS。
実36順・失敗継続・既存出力拒否・preflight/source変更・集計例外のattempt保持、
三採用祖先/棄却probe費用、非fresh/資源失敗の除外、未知秒/誤差、両反復と型/偽判定を確認した。
runnerの36起動は制御mockで、新FEMは0。実04の保存長球1 eventを新求解なしに集計し、
PAUSEDが確認達成へ昇格しないことも確認した。
先行未実装ImportError、fixtureの採用親宣言の誤りを別logで保持した。
最後の図のmarker変更は表示だけで、成功unit/FEMの繰返しは不要とした。

FEM/場/RF/指標/公開停止と原計画/閾値は不変。新依存/外部資料/legacyはない。
この段階でseed/full/GUI/Hosted CIと固定36の数値結果を合格と主張しない。

## 固定実行

```sh
UV_CACHE_DIR=/tmp/superfish-uv-cache OPENBLAS_NUM_THREADS=1 \
uv run --no-project --python .venv/bin/python python scripts/validate_curved_rf_goal_efficiency.py \
  --source-archives out/n04-rf-goal-termination-20261014/accepted-source-archives.json \
  --source-archives-sha256 3f4ea774098d7257a2bf0633b36987750a72c52605ec3af7ca7d062bea34366c \
  --out out/n04-rf-goal-fixed36-20261014
```

コード/sourceを固定し、他の重い検証が終端した状態で開始する。
同じ途中計測行を別プロセスで再開して、元の無中断36行へ混ぜない。
終了後にsource/全量/各停止・未達/相似則、両反復の精度と費用を監査して05を判定する。
