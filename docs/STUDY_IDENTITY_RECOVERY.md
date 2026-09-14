# D01 完了済みStudyでの個別ID回復

2026-09-14：[逐次Studyの個別ID回復と再開](TRACKED_STUDY_IDENTITY_RECOVERY.md)を要求版2・CLI/JobManager/GUIへ接続。
回復指定を完了Studyと共有し、回復前後の停止・再開、未確認時の次点未計算、元JSON重複拒否と回復状態表示を追加した。
新7/関連44unit、独立20FEM・再作成worker8FEM、既存18保存解再検証、Chrome新16/旧11/適応10項目が合格。
適応Study・tuneへの回復接続と親D01は継続中。親33=9/17/6/1、goal ACTIVE。以下は各段階の記録。

2026-09-14。完了したStudyの保存場追跡へ、指定点での[個別ID回復](MODE_IDENTITY_RECOVERY.md)を接続した。
要求版2で回復する点・過去の基準点・比較条件を明示する。成功後の隣接比較は回復済みIDを継承し、
失敗時は元の集合を保持して後続点を未追跡として保存する。独立に計算済みのStudy結果とnative場は変更しない。
親D01と全計画は継続中。逐次Study・適応Study・tuneの自動回復は後続である。

## 入力と処理

`build_study_mode_tracking`、`save_study_mode_tracking`および`track-study-modes`は、
従来の要求版1に加え、次の構成の版2を受け入れる。

```json
{
  "schema_version": 2,
  "study_run": "study",
  "initial_ids": ["TM010", "TM020", "TM011"],
  "step_controls": [],
  "identity_recoveries": [
    {
      "point_index": 2,
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
  ]
}
```

上はキー構成の説明である。`step_controls`には隣接する全点対の制御を従来どおり指定する必要があり、
空配列のままでは実行できない。版2の`identity_recoveries`も空配列を許さない。
`point_index`と`anchor_snapshot_index`はいずれも0始まりのStudy点番号で、anchorは回復点より前でなければならない。
回復点は厳密増加で、重複・bool・範囲外・未知キーを拒否する。到達前に停止する場合も全指定の入力を検査する。

各回復のcontrolsは、隣接比較と同じ写像契約を使用する。形状法則を持つ曲線Studyでは、
指定したanchorと回復点の実際の値からアフィン写像または二次比較メッシュを導出する。
隣接点用の写像を離れた二時点へ転用しない。回復比較では集合へのまとめ直しを許さない。

各点の隣接比較がPASSのときに、指定があれば回復を検査する。回復対象がすでに全個別ID確定、
またはanchorが個別未確定なら入力エラーになる。対応が曖昧・縮退・既存集合と矛盾する場合はUNVERIFIEDで保存し停止する。
後続の点を飛ばして再開する機能はない。元要求と未到達の指定は保存され、未追跡点のIDはnullとなる。

保存文書は`study_mode_tracking`版2で、内側の履歴に回復があれば`mode_tracking_history`版3となる。
`point_results`は回復後の実効IDと状態を示し、`identity_recovery_status`はその点の回復状態、実施しなかった点はnullを示す。
内側の元比較は保持されるため、元比較PASS・回復UNVERIFIEDを区別できる。
再生では全Study宣言・点順・元場・回復計画・回復結果・表示用点要約を再計算して一致を要求する。

```sh
python -m superfish_ng track-study-modes request.json --out study-tracking.json
python -m superfish_ng replay-study-mode-tracking study-tracking.json
```

GUIでは従来形式を含むStudy追跡文書を開き、「以前の保存場から個別IDを回復」で過去の点を選べる。
この操作は追跡末尾に回復指定を追加し、Study全体の元保存場から再検証した別の追跡文書を作る。
APIは`recover_study_mode_identities(document, request)`で、requestは`anchor_snapshot_index`と`controls`。
GUI要求は元JSON文字列を解析し、重複キーも拒否する。成功後は点一覧へ個別IDを表示し、失敗後も文書を保存できる。
複数の回復点を事前指定する操作はCLI/APIの要求版2で行う。GUIで新しい隣接点を足す操作は従来どおり無効である。

## 検証と範囲

開始HEADは`b14b62e`。索引は`out/study-identity-recovery-20260914/acceptance.json`。
数値要約は`benchmarks/tracking/study-identity-recovery-20260914.json`。

最初の試験fixtureはNumPyの浮動小数を厳密Study入力へ渡して拒否されたため、Python floatへ修正した。
その後、円筒解析縮退を2回通る6点で、要求版2不在による変更前の失敗を確認した。
新7unitは7.217秒PASS。新7件と直接利用先の計50件は19.852秒PASS。
対象は`test_study_identity_recovery`、`test_study_mode_tracking`、`test_mode_identity_recovery`、
`test_mode_tracking_history`、`test_gui_mode_tracking`、`test_tracked_study`、`test_adaptive_study`、`test_studies`。
回復後の順位交換、回復済みanchorの再利用、失敗停止、未到達条件の厳密入力、元Study不変、改変拒否、CLI/GUIを確認した。
曲線Studyの直接利用先3件は237.351秒PASS（アフィン・非アフィン・再メッシュの完了Study保存追跡/再生）。
表面収束の直接利用先1件も7.055秒PASS。初回は幾何拒否が個別ID検査より先だったため、実GUIの固定幾何拒否と元比較の個別ID拒否を分けて確認した。
最終は50+3+追加1=54件の分割証拠、新テストは8件。後から回復しても過去の未確定な比較を表面収束へ流用しない。

専用検証は基準・全長2倍・保存エネルギー4倍の各6点、計18実FEMを保存した。
Bessel解析の最大周波数差5.614e-6未満、求積次数12/18の複数回復・継続・縮退拒否・CLI再生を確認。
縮退点を除く4点の全3モードで、周波数・両R/Q・Gと内部16点のHおよびEの尺度則を別に検査した。
最大RF差5.063e-14、場差3.106e-14。

初回は電場各成分を自身のノルムで割った検証器の判定で停止した。
問題のTM010のErは解析上0で、数値Erの大きさは電場全体の約4.157e-6。
その成分での相対差2.428e-9に対し、電場全体に対する差は1.010e-14だった。
電場ベクトル全体のノルムで比較するよう検証器を直し、同じ18保存解を再検証して19.333秒PASS。
追加FEMは0。製品・許容差2e-9・元場を変えず、失敗記録と全成分診断を保持した。

Chromeの新版8項目と共有パネルの単独履歴17項目がPASS。外部HTTP0、新FEM0。
以前のStudy文書の読込、末尾回復、元比較保持、保存再生、複数回復、anchor改変拒否、未追跡点表示を確認した。
数値検証中1064ソース系ファイルは不変。その後の差はStudyブラウザー検証器と追加の表面収束テストだけで、325製品SHAはブラウザーと最終実装で一致する。
元Study/nativeの282ファイルも不変。画面を目視し、取込3ジョブ完了後に専用GUIを終了した。

FEM・RF定義・規格化・旧mode_index・旧要求版1の意味は維持する。
新しい文献・依存・旧資産の参照はない。全suite・seed・Hosted CI・新Wine比較は今回未実行。
指定した保存場間の再同定であり、連続した物理枝の証明ではない。
親33=9受入/17進行/6他未受入/1範囲外、goal ACTIVEを維持する。
