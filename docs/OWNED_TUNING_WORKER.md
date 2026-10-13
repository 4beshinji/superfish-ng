# Hφ所有workerの共通契約

2026-10-14 **RF-04 DONE**。RF-03の固定full終端/受入後に、検証済み四ファイルを主ツリーへ反映した。

`owned_tuning_worker.py`が投入、queued/running/complete/failed、所有snapshot、manifest、
完全保存再生の外側とcheckpoint prefixを扱う。直線、曲線、材料の各adapterはkind、
入力/結果ファイル名、physics、worker moduleを明示した`OwnedTuningContract`を渡す。
submission/所有コピーの検査、native再生、試行実行、結果文書化は名前付きcallbackで渡す。
kindから物理を推測せず、汎用基底クラスや新manifest/schemaを導入しない。

下位の依存は標準ライブラリと`input_validation`、`json_codec`、`artifact_provenance`のみ。
Case/Project、JobManager、GUI、FEM/RF核はimportしない。JobManagerの方針、数値式、
旧入口signature、試行/判断/保存形式、専用parserは維持する。

| 元の契約 | 直線Hφ | 曲線Hφ | 材料Hφ |
|---|---|---|---|
| 新規試行予算 | Noneまたは整数1以上 | 同左 | 同左 |
| 完了workerの追加試行 | 1以上 | 同左 | 同左 |
| checkpoint番号 | 1以上 | 0以上 | 0以上 |
| ファイル名 | 元の番号解釈を保持 | checkpoint-NNN.json | checkpoint-NNN.json |
| 必須prefix | 提供された異なるprefixと最終地点 | 継承offsetから最終地点まで全て | 同左 |
| 保存結果のtrial path | 元の絶対path | basename。読込時は所有pathへ復元 | 同左 |
| 所有入力検査 | 専用checkpoint形状検査 | 元JSON型/厳密キー/schema/SCOPE検査 | 同左、材料専用 |

初期checkpoint-000は新規試行数ゼロの許可を意味しない。全系で予算と実追加数を検証する。
投入入力のhash、native/Projectの正確なfile集合、所有path、継承祖先、全RFと判断履歴、
検査前後の内容を確認し、改変・リンク・欠落・別kindを拒否する。
元出力が移動しても所有コピーから再生できるが、失われたコピーの修復は行わない。

検証は自作sourceの隔離コピー`/tmp/superfish-rf04-owned-workers-20261014`で行った。
rawは`out/rf04-owned-workers-20261014/`、最終候補の束縛は
`verification-preparation-acceptance.json`と`verification-candidate.patch`。

- 三系workerの14個別unit：実pause/resume/cancel、管理器再生成、失敗prefix、
  元出力/所有worker移動、kind/改変/リンク拒否。段階ごとの元失敗も保全。
- 三系GUI serviceの6個別unit：保存地点選択、再開、元Project/native復元、管理器再生成、
  所有コピー利用、別物理拒否。HTTP/実ブラウザー操作の受入ではない。
- 元/抽出workerの実比較：各系2試行ずつ両版、計12新FEM。native/Project byteと、
  job rootだけを対応させた全結果/全RF/判断は完全一致。6成果物を最終共有検証で再生し、
  owned byteは前後不変。追加求解を呼ぶと失敗する条件で、新FEMゼロを確認。
- 共通機構の旧body AST、prefix policyの定数展開、九つの物理/所有入力body、
  全旧関数signatureを照合。下位importだけであることも確認。

20テスト後に六つの契約constructorを位置引数から明示keywordへ変更した。
`factory-keywords.json`でfield束縛と評価順序が同じことを確認し、最終AST監査もPASS。
テスト時点のsource mapを残し、宣言だけの変更に同じFEMを再実行していない。
主ツリー反映時に検証済み四ファイルのhash一致と他1489 sourceの不変を確認した。
`main-applied.json`が元/反映後source一覧と隔離検証receiptを束縛する。
初回の反映前hash確認はraw basenameの解決先誤りで停止し、コピー前に修正した。

JobManagerと数値核への変更はなく、RF-04単独のfull/seed再実行は不要と判断した。
これは既存の解析場/量別精度条件や未確認statusを緩める変更ではない。
tracking/historyの他worker、CLI/HTTP/画面分離、再生費用は後続カードで扱う。
