# D01 適応Studyの元目標に結び付けた個別ID回復

2026-09-14。適応Studyの要求版2で、指定した元目標へ到達した際に
[個別ID回復](MODE_IDENTITY_RECOVERY.md)を行い、チェックポイント版3へ根拠を保存する。
中点が増えても参照する元目標を変えず、回復前後の停止・再開をAPI/CLI/JobManager/GUIで扱う。
これはD01/P2-01の限定課題であり、親D01・tuneへの接続・一般写像の残件と全計画は継続中である。

## 入力と参照先

従来要求の`schema_version`を2にして、空でない`identity_recoveries`配列を追加する。
各指定は次の3キーだけを持つ。番号はすべて0始まり。

| キー | 意味 |
|---|---|
| `target_index` | 回復する元目標番号。初期目標より後、重複なく厳密増加 |
| `anchor_target_index` | 参照する以前の元目標番号。回復目標より前 |
| `controls` | この二つの実形状間の個別場比較条件。集合へのまとめ直しは禁止 |

ここでの番号は入力`study.values`の位置であり、計算順や採用履歴の位置ではない。
たとえば元目標0→1の比較が失敗し中点を挿入すると、計算点は0・1・中点の順、
採用履歴は0・中点・1の順になる。元目標1を参照する指定は採用履歴の位置2へ結び付く。
追加中点では回復しない。二分後の深さが1以上でも、元の目標値へ到達した時点で指定を適用する。

全指定の型・順序・範囲・未知キー・比較条件を出力作成前に検査する。
形状法則を伴うStudyでは、共有する`study_identity_recovery.recovery_requests`が
指定した元目標の実Projectから写像を導出する。採用履歴への結び付けは実行時に行い、
参照点で全個別IDが確認済みであることを既存回復APIが検査する。過去に回復済みの元目標も参照できる。

## 採用・停止・保存

隣接点の比較がPASSとなってから回復を試みる。以前の確認済み場との全個別対応と、
現在の継承集合内のID一致を満たしたときだけ、回復後の履歴と現在点を採用する。
曖昧・縮退・集合境界違反で回復がUNVERIFIEDなら、次のように保存して停止する。

- `decision="STOP"`、`stop_reason="identity_recovery_unverified"`。
- 直前までの採用履歴を保持し、回復を試みた現在点は未採用・元目標は未到達とする。
- 隣接比較のPASSと回復失敗の全イベントを同じattemptに保存する。
- 二分の追加・後続点のFEM・UNVERIFIED文書からの再開は行わない。

参照点が個別ID未確認であるなど、回復APIの前提に反する指定は入力エラーになる。
後続計算が失敗しても、以前のチェックポイントを変更しない。
逐次Studyと異なり、失敗候補は主履歴へ採用せずattemptへ根拠を残す。

要求版2は外側の`adaptive_tracked_study`版3を使用する。
各attemptの`identity_recovery`は未実施ならnull、実施時は次を保存する。
`target_index`、`anchor_target_index`、`anchor_point_index`、`anchor_snapshot_index`、
`current_point_index`、`status`、および内側の回復履歴版3の全`event`である。
要求版1・チェックポイント版1/2の従来の意味は保持する。
再生は元の保存場から判断と結び付けを再構築し、番号・イベント・採用順・版の改変を拒否する。
再開は要求の完全一致と全祖先の検証を要求し、既存点を再計算せず別の出力先へ続ける。

`max_attempts`と`max_new_attempts`は隣接比較の回数を数える。
回復比較はこれと別で、各指定元目標につき最大1回追加する。
GUIは隣接比較の予算、回復実施数/指定数、各試行の元目標と回復状態を表示する。
元JSON文字列の重複キーを拒否し、再開では入力欄の編集を使わず保存要求を使用する。

```sh
python -m superfish_ng execute-adaptive-study request.json --out first --max-new-attempts 1
python -m superfish_ng replay-adaptive-study first/checkpoint-001.json
python -m superfish_ng resume-adaptive-study first/checkpoint-001.json --out continued
```

## 独立検証と受入範囲

開始HEAD `2992794`。索引は`out/adaptive-study-identity-recovery-20260914/acceptance.json`、
数値要約は`benchmarks/tracking/adaptive-study-identity-recovery-20260914.json`。
元目標と挿入後の履歴を取り違えないこと、回復失敗時に採用済み接頭部分を保持することを受入条件とした。
要求版2が存在しない変更前の失敗を記録し、最初の2不変条件を22.074秒で確認した。

新`test_adaptive_study_identity_recovery`の8件は41.647秒PASS。
実中点挿入、回復済み参照点の再利用、逆向き目標、全指定の事前拒否、番号/イベント/再開要求の改変拒否、
後続FEM失敗時のチェックポイント保持、CLI、JobManager再作成とGUI transportを確認した。
関連46件は83.750秒PASS。対象は`test_adaptive_study`、`test_adaptive_resume`、
`test_adaptive_study_jobs`、`test_gui_adaptive_study`、`test_gui_tracked_study`、
`test_tracked_study_identity_recovery`、`test_study_identity_recovery`、`test_mode_identity_recovery`。
54件の二つの実行記録であり、全suiteの受入ではない。

独立解析円筒はR=0.1 m、L=0.04/0.055/解析交差長/0.075/0.08/0.085 m、P2・8×8・3モード。
最初の3解pilotで長さ0.04→0.055の最小重なり0.999999997779、
中点0.0475を挟む二比較0.999999999108/0.999999999674を確認した。
その間の固定閾値0.9999999988で実二分を発生させ、実装後の許容差緩和は行っていない。
TM020/TM011の解析縮退を通過した後に回復し、後半では明示gap=0.2による近接周波数集合を再び分離・回復する。
後半を二つ目の物理縮退とは扱わない。

専用`validate_adaptive_study_identity_recovery.py`は基準・全長2倍・U4倍の各7解と
失敗停止4解、計25新FEMを37.820秒でPASS。pilotの3解はこの25解に含まない。
停止1→追加2→追加2で最初の回復後に停止→残りへ再開し、360保存ファイル不変とCLI再生を確認した。
求積次数12/18で同じ判断となり、逆向き掃引も正しい個別IDへ戻る。次数変更・逆向きは保存解を再利用し、新FEM0。
Bessel解析周波数の最大相対差2.742e-5未満（事前閾値0.002）。
縮退点以外の6点×3モードで周波数・両R/Q・Gと内部16点のH/E尺度則を別検査し、
最大RF差5.219e-14・場差1.872e-14（事前閾値2e-9）。電場は全ベクトルのノルムで比較する。

別workerの11新FEMは17.482秒PASS。JobManager再作成後の再開と回復失敗停止を確認し、
完了7点の全保存配列・RFは直接実行と完全一致した。
Chrome新版15/旧適応版10項目PASS、外部HTTP0。原JSON、元目標への結び付け、保存・再読込・改変拒否、
回復済み点を参照する再開、失敗停止、中止を検証した。GUIで完了した新FEMは16解。
GUI新版の7点も直接実行と全保存配列・RFが完全一致し、210元ファイル不変、新FEM0で確認した。
画像を目視し、全12GUIジョブ（10完了・2中止）の終端後に専用サーバーを終了した。
実行の一部は並行しており、記録時間を単独性能と扱わない。

専用実行の1070ソース系とブラウザーの327製品SHAは最終実装と一致し、実行中不変。
FEM・求積・規格化・RF定義・周波数順位は変更していない。新文献・依存・旧資産参照はない。
全suite/seed/Hosted CI/新Wine比較は今回未実行。保存二時点での再同定を連続した物理枝の証明と扱わない。
親33=9受入/17進行/6他未受入/1範囲外、全計画goal ACTIVEを維持する。
