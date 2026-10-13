# RF版5対照：専用CLIと外側の終端費用

2026-10-14 JST、`ADD-N04-rf-goal-04` の限定受入。04は **IN_PROGRESS**。
固定36実行05、GUI/原条件監査06、親N04と全計画は未完。

## 変更と受入条件

`scripts/run_curved_rf_goal_efficiency.py` で固定36行のうち一行を起動し、
PAUSED結果を別出力先へ再開し、元journalまたはprocess bundleを完全再生する。
`--max-new-events` は開発用の一時停止条件であり、固定benchmarkの予算を変更しない。
比較用の新規CLIで、公開版5の選択・停止・保存schemaは変更していない。

受入条件は、不正入力/未知行/既存出力を求解前に拒否し、実終了・stdout/stderr・
部分ファイルと前後source一覧を保持すること。ゼロ終了だけでは物理受入を宣言しない。
最終resultの書込を含む外側wallと書込部分のwallを区別し、合算による二重計上を避ける。
readerは完成したnativeの全場/RF/元判断を追加固有求解なしに再構築する。

## 実行方法

環境はプロジェクトのuv runnerを使用する。このsandboxではuv cacheを `/tmp` に置いた。
`source-archives.json` は元SHA256から絶対アーカイブpathへの明示mapping。
下のmapping SHAは今回のローカル証拠用で、別checkoutのpathへ無断で置換しない。

```sh
UV_CACHE_DIR=/tmp/superfish-uv-cache OPENBLAS_NUM_THREADS=1 \
uv run --no-project --python .venv/bin/python python \
  scripts/run_curved_rf_goal_efficiency.py run \
  --execution-id sphere-scale-1-repetition-1-uniform --max-new-events 1 \
  --source-archives out/n04-rf-goal-cli-20261014/source-archives.json \
  --source-archives-sha256 19cec4f6f7f40d0129c49f0673d186491bcd1c16bf9ef1fc18420b844f21fe05 \
  --out out/rf-goal-cli-new
```

`resume --journal <元result> --sha256 <元SHA> --out <新directory>` は元要求を保持する。
`replay --journal <元result> --sha256 <元SHA> --out <新report.json>`、または
`replay --bundle <元manifest.json> --sha256 <元SHA> --out <新report.json>` を使用する。
元ソースにアーカイブが必要なら同じ `--source-archives` とそのSHAを渡す。
中断入力の `--interruption-files` とそのSHAは、既存のSIGINT再開契約へ転送する。
今回の新実行は開発PAUSEDからの再開であり、一般kill再開の受入には使わない。

## 保存と時間の意味

supervisorは既存 `run_measured_process` のLinux wait4/RSS監視を再利用する。
固定の3600秒/32 GiB、BLAS 1 thread、CPU求解を保持する。
RSSはsampleと終端high-waterで、連続した資源上限の保証とは呼ばない。
process wallは起動/importから終端/reapまでを覆う。

`worker-terminal.json` はAPI呼出しから最終result公開/returnまたは例外までのinclusive wallと、
その部分集合であるresult書込wallを保持する。receipt自身の書込とinterpreter終了は
process wallに含まれる。元 `observed_cost` のphaseと時間は書き換えない。

`manifest.json` はinvocation、環境、全1509 sourceの前後一覧、process実終端とlogs、
native/checkpoint/全域sample、失敗/部分stagingの全ローカルfileを束縛する。
bundle再生は一覧/追加/欠落/byte差とsource差分の算術を確認し、その後に元journalを完全再生する。
manifestのhash照合だけで科学的整合性や実時間の真正性を保証するものではない。
未公開stagingをcheckpointへ昇格せず、非成功processと未知/欠落のworker結果を保持する。

## 参照ソースの復元

最初の実CLIは `affine_saved.py` の旧参照SHA差で停止した。`fresh/` の実終了1、
ValueError、stderrと終端receiptを保持し、成功記録へ変更していない。
参照readerへ明示 `source_archives` を追加し、fresh workerと既存saved/resumeへ接続した。
元の期待SHA・参照manifest・全域配列・数値条件は変更しない。アーカイブは実行しない。

52元fileは自作実装のgit履歴から完全一致するbyteを取得した。
旧生成 `PKG-INFO` は元README/header、`SOURCES.txt` は同じ履歴の93項目から復元し、
いずれも元manifestの既定SHAと完全一致したものだけを使用した。
元アーカイブ・現行ソース・旧8個のaliasを上書きせず、提供した全archiveもreferenceへ束縛する。
未入手byteのSHAを書き換えたり、現在のソースを元ソースへ偽装する処理はない。

## 検証結果と範囲

rawは `out/n04-rf-goal-cli-20261014/`、監査は `acceptance.json` と `audit.py`。
CLI新7/参照archive新1を含む51個別unitが22.098秒、終了0/PASS。
対象は新CLI、reference、worker、resume、saved、costs、既存processの7module。
後のarchive束縛とstrict空list拒否は影響する5件/1件だけ再確認し、成功済みの全体を繰り返していない。
先行未実装FileNotFoundErrorとuv cacheのread-only失敗も別logで保持した。

| 新しい実process | 終了 | 秒 | 最大RSS byte |
| --- | --- | ---: | ---: |
| 旧参照SHAで停止 | 1 / PROCESS_FAILED | 1.304598 | 89153536 |
| 球一様の1 event | 0 / PROCESS_EXITED、PAUSED | 7.018150 | 95031296 |
| 同prefixから追加1 event | 0 / PROCESS_EXITED、PAUSED | 14.691503 | 96575488 |

新FEMは2回、二つのbundle完全再生は新固有求解0。
元無中断の同水準との29 native/sample配列は全byte一致、全mode/RF辞書も完全一致。
両R/Qの2倍関係とUe/Uhの0.5 Jからの相対差最大1.333e-15を確認した。
元prefixの全event/native/sample/費用は再開結果の先頭で完全一致する。
最終result書込は新規0.007391秒/再開0.008720秒で各外側wallに包含される。
三processとも前後1509源UNCHANGED、終端PID不在、全handleは終端。
CLI三操作の実argv/終了値/時間は `cli-commands.json`。

元worker loop、独立場sampling、数値停止、referenceの解析/写像関数はAST不変。
関連unitの独立Maxwell/Green/energy/尺度則を保持した。
数学核・依存・公開保存版・閾値への変更はなく、新seed/full/GUI/Hosted CI/legacy実行は0。
2026-10-14の過去fullを今回の新sourceのfull受入と呼ばない。

04にはSIGTERM/SIGKILLからの一般再開と、その非成功bundle/全prefixの統合受入が残る。
全152カードは102 DONE/3 IN_PROGRESS/47 PLANNEDを維持する。
