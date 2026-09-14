# D01 分裂後の個別モードIDの回復

2026-09-14：[逐次Studyの個別ID回復と再開](TRACKED_STUDY_IDENTITY_RECOVERY.md)を要求版2・CLI/JobManager/GUIへ接続。
回復指定を完了Studyと共有し、回復前後の停止・再開、未確認時の次点未計算、元JSON重複拒否と回復状態表示を追加した。
新7/関連44unit、独立20FEM・再作成worker8FEM、既存18保存解再検証、Chrome新16/旧11/適応10項目が合格。
適応Study・tuneへの回復接続と親D01は継続中。親33=9/17/6/1、goal ACTIVE。以下は各段階の記録。

2026-09-14：[完了Studyの個別ID回復](STUDY_IDENTITY_RECOVERY.md)を要求版2・API/CLI/GUIへ追加。
指定点で過去の個別場と継承集合を照合し、成功後は後続点へIDを渡す。失敗後の点は未追跡として保存する。
関連54unitの分割証拠、18保存解の解析/尺度則、新GUI8項目と単独履歴17項目が合格。逐次/適応Study・tune接続と親D01は継続中。
以下の「Study未接続」は完了Studyの回復を追加する前の記録。

2026-09-14。以前に個別IDを確認できた保存場と履歴末尾の保存場を明示的に比較し、
合流・分裂後に保持していたID集合を個別IDへ戻すAPI・CLI・単独履歴GUIを追加した。
元の比較段階とnative場は変更せず、履歴版3の独立した回復イベントとして根拠を保存する。
親D01は進行中。Study・逐次/適応Study・tuneによる自動回復は未接続である。

## 受入条件と判定

今回の対象はBACKLOG P2-01の「分裂後の個別枝回復」の保存履歴経路。
独立な座標固有空間の番号交換で、周波数順位とは異なるID順を回復することを変更前の失敗で確認した。
別の負例では、全体の場対応が一意でも既存ID集合の境界を越える候補を拒否する。

回復元の時点をanchorと呼ぶ。履歴がPASSで、末尾に未確定の個別IDが残る場合だけ要求できる。
anchorは末尾より前で、全個別IDが確認済みでなければならない。
既存の重み付き場比較により、次の両条件を満たしたときだけ全体をPASSにする。

- anchorから末尾への比較がPASSで、全モードが個別に対応する。集合へのまとめ直しは使用しない。
- 末尾の各既存ID集合について、その要素へ割り当てた候補IDの集合が、継承したID集合に一致する。

一部だけの回復は行わない。曖昧・縮退・集合境界違反はUNVERIFIEDイベントとして保存し、
回復前のID集合と個別IDを保持する。その新履歴の継続は停止するが、元の履歴は別に保持できる。
入力の不備、元ファイルの変更、保存内容と再計算の不一致は入力エラーになる。

これは指定した二時点の場による再同定である。縮退区間を通る連続した物理枝を証明するものではない。
周波数順位、固有ベクトル、規格化、RF値を差し替えたり、解析式でFEMを補正したりしない。

## 要求と保存形式

`mode_identity_recovery.recover_mode_history(history, request)`の要求は次の2キーだけを許す。

```json
{
  "anchor_snapshot_index": 0,
  "controls": {
    "mapping": "normalized_cylinder",
    "sample_order": 12,
    "minimum_overlap": 0.98,
    "minimum_assignment_margin": 0.05,
    "relative_cluster_gap": 0.001,
    "minimum_relative_singular_value": 1e-8
  }
}
```

番号0は最初の比較のprevious側、番号i+1はsteps[i]のcurrent側である。
その時点に以前の回復イベントがあれば、回復後のIDを使用する。
nativeパスは検証済み履歴から導出し、要求で別の保存場を差し込まない。
controlsは既存の保存場比較の厳密入力を使用し、`cluster_transition_policy`を禁止する。
例の閾値・円筒写像は専用検証条件であり、異なる形状へ自動採用する既定値ではない。

履歴版3は元の`steps`を保持し、`identity_recoveries`を追加する。
各イベントは0始まりの`after_step_index`、要求、実比較、集合の整合判定、状態と適用範囲を保存する。
配置番号は厳密増加で、同じ段階に複数の回復を挿入できない。
再読込では全比較と回復を元の順序で再計算し、保存場の同一性、実効IDの連続性、全保存値を照合する。
回復済み履歴への継続では回復後のID集合を使用する。別の合流・分裂後にもう一度回復でき、
以前に回復した時点もanchorへ指定できる。旧履歴版1/2の再生契約は維持する。

```sh
python -m superfish_ng recover-mode-identities split-history.json recovery-request.json --out recovered-history.json
python -m superfish_ng replay-mode-history recovered-history.json
python -m superfish_ng extend-mode-history recovered-history.json next-step.json --out extended-history.json
```

出力は未使用のパスへ保存する。CLIはPASSで終了0、保存されたUNVERIFIEDで終了1、入力エラーで終了2。
GUIでは単独履歴の「以前の保存場から個別IDを回復」で時点を選び、表示中の写像と閾値で検査する。
成功時は回復比較の個別対応を表へ表示し、元の比較列は保存文書内に残す。
失敗時も保存できるが、次の結果へ継続する操作は無効になる。入力JSONの重複キーは拒否する。

## 検証記録

開始HEADは`9e1c13c`。索引は`out/mode-identity-recovery-20260914/acceptance.json`。
小さな数値記録は`benchmarks/tracking/identity-recovery-20260914.json`。

関連65unitは5.842秒でPASS。対象は新`test_mode_identity_recovery`の9件、
`test_mode_tracking`、`test_subspace_identity`、`test_cluster_transitions`、`test_cluster_repartition`、
`test_saved_mode_tracking`、`test_mode_tracking_history`、`test_profile_mode_tracking`、
`test_study_mode_tracking`、`test_gui_mode_tracking`と、
`test_tuning.TuningTests.test_unverified_and_subspace_stop_before_root_update`。
多重回復・過去の回復済みanchor・元履歴不変・改変拒否・比較中のnative変更・CLI/GUIの厳密JSONも含む。

専用検証器は円筒P2の基準、全長2倍、保存エネルギー4倍について、
TM020/TM011交差前・Bessel零点から求めた縮退長・交差後の各3解、計9実FEMを保存した。
求積次数12/18で合流・分裂・回復・再継続、まだ縮退した場への回復拒否、保存/CLI再生を検査した。
解析周波数の最大相対差は5.614e-6未満。離れたモードでは周波数、両R/Q、Gと内部16点のH/Er/Ezの尺度則を別に検査した。
最大RF尺度差3.220e-14、場尺度差1.848e-14。縮退点の個別基底同士は比較しない。
保存済み場の尺度則診断に限り、両場の全体符号を合わせる。native値は変更しない。

最初の数値実行は9FEMと回復検査後、検証器がnative読込結果に存在しないmass行列をRF再計算へ要求して失敗した。
検証器を実FEMから保存済みのRF値の利用へ直し、`--reuse-native`で同じ9解を新出力へ再検証した。
最終は4.188秒PASS、**追加FEMは0**。初回失敗、修正前検証器、108個のnativeファイルのSHAを保持した。

Chromeは既存8項目と新9項目の計17項目PASS、外部HTTPは0。
既存D01監査の3保存解を取り込み、新FEMを実行せず回復・保存・再生・改変拒否・継続・失敗状態を確認した。
初回は13項目成功後、同名ダウンロードで上書きされた文書を元履歴として読んだ検証器が停止した。
元のダウンロードを別名で保持する修正後、新しいGUI作業領域で17項目を確認した。
最終レビューで、旧履歴版1の確認済み個別IDに対して回復ボタンが有効になる表示不備も再現した。
APIは拒否していた。ボタン条件をID配列から判定するよう修正し、旧履歴の追加2項目と上記17項目を最終製品で確認した。
数値検証中1062ソース系ファイルは不変。以後の差はブラウザー検証器とapp.jsのボタン条件だけで、325製品SHAは最終ブラウザー結果と一致する。
native108ファイルも不変。画面を目視し、全ジョブ完了後に専用GUIを停止、全実行の終了を回収済み。

今回、全suite・seed・Hosted CI・新Wine比較は実行していない。
FEM本体、求積則、RF定義や許容差の変更はなく、新たな外部文献・依存・旧資産の参照もない。
Study/逐次Study/適応Study/tuneへ回復方針を保存・再生する接続と、一般写像の残要件は後続とする。
親33課題の9受入/17進行/6他未受入/1範囲外および全計画goal ACTIVEを維持する。
