# D01 逐次Studyの個別ID回復と再開

2026-09-14追補：[tuneの個別ID回復と保存再開](TUNING_IDENTITY_RECOVERY.md)も接続済み。
指定参照から全個別対応・継承集合整合を確認してから周波数を評価し、未確認なら停止する。
以下のtune未接続表記は当時の状態。次はD01/D02の元要件と最新証拠の照合を行う。

2026-09-14追補：[適応Studyの回復と再開](ADAPTIVE_STUDY_IDENTITY_RECOVERY.md)も接続済み。
元目標番号を採用履歴へ結び付け、失敗候補を主履歴へ採用せずattemptに根拠を保存する。
以下の適応Study未接続表記は当時の状態。tune接続と親D01は継続中。

2026-09-14。逐次Studyの要求版2で、[完了Studyと同じ回復指定](STUDY_IDENTITY_RECOVERY.md)を
実FEM・チェックポイント・CLI・JobManager・GUIへ接続した。指定点で回復した個別IDを後続点へ渡し、
回復前後の一時停止・再開でも指定と根拠を保持する。曖昧な回復はUNVERIFIEDとして保存し、次の点を計算しない。
親D01と全計画goalは継続中。適応Study・tuneの回復方針と保存再開は後続である。

## 要求と保存契約

従来の逐次要求の`schema_version`を2にし、`identity_recoveries`を追加する。
それ以外の`study`、`initial_ids`、`step_controls`は従来契約を保持する。
回復指定は空でない配列で、各要素は次の3キーだけを持つ。

| キー | 意味 |
|---|---|
| `point_index` | 回復を行うStudy点番号。0始まり、初期点以降、重複なく厳密増加 |
| `anchor_snapshot_index` | 以前の個別ID確認済み点番号。回復点より前。回復済みの過去の点も指定可能 |
| `controls` | anchorと回復点の場比較条件。集合へのまとめ直しは禁止 |

`study_identity_recovery.recovery_requests`で、完了Studyと逐次Studyの指定検査を共有する。
形状法則があるStudyの写像は、指定した2点の実際の値とProjectから導出する。
開始・再開前に未到達点を含む全指定を検査する。bool・範囲外・未知キー・不正な比較条件は出力作成前に拒否する。
個別IDが実際に確認済みかどうかは保存場を追跡した時点で検査する。

回復点までの隣接比較がPASSのときに、既存の個別回復APIで全個別対応と各継承集合内のID一致を確認する。
回復元の条件を満たさない指定は入力エラーになる。曖昧・縮退・集合境界違反はUNVERIFIEDとなる。
元比較のPASSと回復のUNVERIFIEDは別に残し、回復後のID・状態を点一覧へ保存する。

チェックポイントは`tracked_study_checkpoint`版2で、内側の回復履歴は版3となる。
`point_results`の`identity_recovery_status`はその点の回復結果、未実施の点はnull。
再開は元要求との完全一致と全祖先の再生を要求し、以前の点を再計算せず新しい出力先へ続ける。
回復後の計算が失敗しても、直前の不変チェックポイントを保持する。
UNVERIFIEDチェックポイントは保存・再生できるが再開できず、後続点はNOT_COMPUTEDとなる。
旧要求/チェックポイント版1の意味は変更しない。

```sh
python -m superfish_ng execute-tracked-study request.json --out first --max-new-points 3
python -m superfish_ng replay-tracked-study first/checkpoint-003.json
python -m superfish_ng resume-tracked-study first/checkpoint-003.json --out continued
```

GUIの既存要求JSON欄へ版2を入力できる。要求は元のJSON文字列でサーバーへ渡し、重複キーを拒否する。
再開は保存文書を使用し、入力欄の編集は反映しない。点一覧の「個別ID回復」は確認済み・未確認・未実施を表示し、
診断には時点・比較条件・集合整合の根拠を残す。適応Studyの開始も同じ元JSON送信経路を使うが、その回復指定はまだ未対応である。

## 検証記録

開始HEAD `2ed8c72`。索引は`out/tracked-study-identity-recovery-20260914/acceptance.json`。
数値要約は`benchmarks/tracking/tracked-study-identity-recovery-20260914.json`。

解析円筒のTM020/TM011縮退・分裂を2回通る6点で、要求版2不在の変更前失敗を確認した。
新`test_tracked_study_identity_recovery`の7件は48.608秒PASS。
以前の点の再計算回数0、回復後の順位交換、回復済みanchorの再利用、失敗前チェックポイント保持、
未確認時の次点未計算、厳密入力、改変拒否、CLIとJobManager再作成後のGUI transport再開を確認した。

関連44件は97.141秒PASS。対象は`test_tracked_study`、`test_tracked_study_jobs`、`test_gui_tracked_study`、
`test_adaptive_study`、`test_adaptive_study_jobs`、`test_study_identity_recovery`、`test_study_mode_tracking`、`test_gui_mode_tracking`。
最終51件の二つの実行記録であり、全unitの一括受入ではない。

専用検証は基準・全長2倍・保存エネルギー4倍の各6点に失敗停止用2点を加え、20実FEM・53.017秒でPASS。
2点で停止→1点追加で回復して停止→残り3点へ再開し、全祖先ファイル不変・CLI再生・次点未計算を確認した。
Bessel解析周波数最大差5.614e-6未満。縮退点を除く4点の全3モードで、周波数・両R/Q・G、内部16点のH/Eの尺度則を別検査し、
最大RF差5.063e-14・場差3.106e-14。電場はベクトル全体のノルムで比較し、解析零成分を相対分母に使わない。
追加の実worker8FEMは26.550秒PASS。JobManager再作成後の再開、失敗回復での停止、直接実行との全6点の全配列・RF完全一致を確認した。

共有した回復指定検査の完了Study側は、既存18保存解を再利用して74.532秒PASS、追加FEM0。
数値検証・新版ブラウザー等は一部並行実行したため、上記時間を単独性能の比較に用いない。

Chrome新版16・旧逐次版11・旧適応版10項目がPASS。元JSON重複拒否、実worker、回復時点の停止/再読込、
回復イベント改変拒否、編集した要求を使わない再開、未確認停止、中止を確認した。GUIで完了した新FEMは合計18解。
新版GUIの6点は直接実行と全保存配列・RFが完全一致し、180元ファイル不変を確認した。
最初の追加照合は全配列/RF一致の後、SHA検証器が文字列にPathメソッドを呼んで失敗した。検証器だけ修正し、新FEMなしで再確認した。
画像を目視し、全16GUIジョブ（13完了・3中止）の終端後に専用GUIを終了した。

全専用実行の1067ソース系と全ブラウザーの326製品SHAは最終実装に一致し、実行中不変。
元のFEM・求積・規格化・RF定義・許容差・周波数順位は変更しない。新文献・依存・旧資産参照はない。
全suite・seed・Hosted CI・新Wine比較は今回未実行。指定保存場の再同定を連続した物理枝の証明と扱わない。
親33=9受入/17進行/6他未受入/1範囲外、goal ACTIVEを維持する。
