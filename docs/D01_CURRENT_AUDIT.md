# D01の元要件と現在の残件 — 2026-09-14

2026-09-14：[逐次Studyの個別ID回復と再開](TRACKED_STUDY_IDENTITY_RECOVERY.md)を要求版2・CLI/JobManager/GUIへ接続。
回復指定を完了Studyと共有し、回復前後の停止・再開、未確認時の次点未計算、元JSON重複拒否と回復状態表示を追加した。
新7/関連44unit、独立20FEM・再作成worker8FEM、既存18保存解再検証、Chrome新16/旧11/適応10項目が合格。
適応Study・tuneへの回復接続と親D01は継続中。親33=9/17/6/1、goal ACTIVE。以下は各段階の記録。

2026-09-14：[完了Studyの個別ID回復](STUDY_IDENTITY_RECOVERY.md)を要求版2・API/CLI/GUIへ追加。
指定点で過去の個別場と継承集合を照合し、成功後は後続点へIDを渡す。失敗後の点は未追跡として保存する。
関連54unitの分割証拠、18保存解の解析/尺度則、新GUI8項目と単独履歴17項目が合格。逐次/適応Study・tune接続と親D01は継続中。
以下の「Study未接続」は完了Studyの回復を追加する前の記録。

追補：監査後に[単独履歴の個別ID回復](MODE_IDENTITY_RECOVERY.md)を実装・限定受入した。
過去の個別場と継承ID集合の整合を要求し、API/CLI/GUI・保存版3・再生と継続を接続。65unit・9保存解・Chrome17項目と旧履歴2項目が合格。
下表と本文は開始HEAD db8cd8fでの監査記録である。「回復APIがない」は本追補の単独履歴経路で解消した。
Study/逐次・適応Study/tuneへの回復方針とイベントの接続、一般写像全体の受入は残り、親D01は進行中を維持する。

開始HEAD `db8cd8f`。D03版3の36FEM受入後、依存D01/D02/N03のうちD01を照合した。
`COMPATIBILITY_PLAN.md`のD01.S/I/Vだけでなく、BACKLOGのP2-01と
「後続として完遂する」「一般写像と個別枝回復の要件は撤回しない」という記載も対象に含める。
古い段階の未実装表記を現在の不足と即断せず、後半の追補・現行コード・実行結果へ照合した。

**親D01は進行中のまま。個別枝回復が未実装であり、受入完了へ変更しない。**
親33=9受入/17進行/6他未受入/1範囲外。D02/D03もこの監査では親受入へ変更しない。

| 要件 | 現在の実装と証拠 | 判定 |
|---|---|---|
| 依存C01.S・現場評価API | MODEL_CONTRACTの共通モデル契約、native読込と元場評価。円筒・profile・曲線比較が利用 | 接続済み |
| .S 異形状の写像・重み | MODE_TRACKINGの円筒/profile/対応メッシュ、曲線比較版2〜4。正重みと可変体積を保持 | 宣言された写像の範囲で確認済み |
| .S 近接/縮退・曖昧判定 | 正規化した重み付き部分空間、全ランク・最悪主角・行列両側の割当余裕 | 今回の解析行列・実FEM検査PASS |
| .I overlapと安定ID | 周波数順位を変えず、個別ID/ID集合/未確認を区別。元場・閾値・写像を保存 | 今回のAPI/CLI/履歴検査PASS |
| .I 失敗/交差の履歴 | UNVERIFIEDを保存し、旧履歴の変更・不連続・ID差替えを拒否。Study/GUI/tuneへ接続 | 今回の選択検査PASS |
| .V 解析交差/近接 | 2×2の独立対称行列、円筒TM020/TM011の順位交換と解析縮退長 | 今回の専用2+3実FEMでPASS |
| .V 符号/番号置換・縮退基底回転 | 直交/可逆な基底変更、重み付き標本順、極端な正規化倍率 | 今回の選択検査PASS |
| .V 追跡不能時のtune制限 | tuning._assembleが全個別ID未確定ならfrequency_hz=null、UNVERIFIEDで停止 | 実tuneの負例PASS |
| BACKLOG: 多対多再構成 | retain_connected_subspace、REPARTITION、旧policy維持。集合内部のIDは未確定 | 既実装。追加6unit・専用1FEMでPASS |
| BACKLOG: 分裂後の個別枝回復 | 現行の合流/分裂/再構成はID集合を保持し、個別IDへ戻す要求/API/履歴イベントがない | **未実装** |
| BACKLOG: 一般写像 | 非アフィン曲線の可変体積・独立FEMメッシュ、番号対応・異なる細分履歴の共通積分まで実装 | 対応しない初期比較分割等は未対応。一般写像全体の受入は保留 |

今回の「多対多」は同じ保存場に意図的な不確定ID集合を与えた検査であり、
その集合が実際の形状掃引で生まれた証拠ではない。
ID集合を一つにまとめて追跡できることと、個別枝を回復できることを区別する。

## 今回の検証

製品コードを変更せず、次の50件を4.089秒で確認した。
`test_mode_tracking`、`test_subspace_identity`、`test_cluster_transitions`、
`test_saved_mode_tracking`、`test_mode_tracking_history`、`test_profile_mode_tracking`、
`test_study_mode_tracking`、`test_gui_mode_tracking`と、
`test_tuning.TuningTests.test_unverified_and_subspace_stop_before_root_update`。
後半の追補で現行の多対多経路を特定し、`test_cluster_repartition`の6件を0.308秒で追加確認した。
計56件は二つの実行記録であり、単一の全suite実行ではない。

以下の既存専用検証器を現在のコードで実行した。新規出力のみ使用した。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_mode_tracking.py --out out/d01-original-acceptance-20260914/crossing
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_cluster_transitions.py --out out/d01-original-acceptance-20260914/cluster
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_cluster_repartition.py --out out/d01-original-acceptance-20260914/repartition
```

全3コマンドが終了0、計6新FEM。円筒交差の解析周波数相対差最大5.601e-6、
縮退長0.06322753439669529 mでの周波数差最大5.614e-6、数値縮退の相対幅1.029e-6。
標本次数12/18で同じ順位交換・集合継承を確認した。
多対多用5モードの解析周波数相対差最大2.553e-5で、次数12/18の両方が合格した。
既存の閾値を変更せず、1059ソース系ファイルは全専用実行中と終了後に不変。

証拠は `out/d01-original-acceptance-20260914/`、索引は同 `audit.json`。
既存の曲線比較・版4共通分割・Chromeの根拠は、それぞれの専用受入記録を参照した。
今回新たに曲線比較の全受入、ブラウザー、全suite、seed、Hosted CI、Wine比較を実行したとは扱わない。
FEM/場/RF/閾値の変更、新規外部数学資料・依存・旧資産の参照はない。

## 次の実装判断

次の限定課題は、個別枝回復の条件と保存契約を先に定め、実装前に独立な失敗例を作ること。
単なる周波数順位、縮退空間の任意の基底、ID名の一致から個別枝を作らない。
以前の個別IDが確定した保存場と回復候補を、宣言された物理写像・重みで比較する方法を検討し、
現在の集合との整合、割当の一意性、未回復理由、参照した元場を記録する。
以前の場がない、候補がまだ縮退している、方向喪失や競合がある場合は回復しない。

受入には、独立な解析交差と縮退基底回転、符号/尺度/番号置換、
実FEMの合流→分裂、曖昧/欠落の負例、元保存不変、完全再生/改変拒否、
履歴・Study・tune・GUIへの明示的な接続が必要。
両端の標本対応を連続経路全体の物理枝の証明と呼ばず、その制限を結果にも保持する。
この記述は次の設計案であり、個別枝回復を実装済み・受入済みとする根拠ではない。
