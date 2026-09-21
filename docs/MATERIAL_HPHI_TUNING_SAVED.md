# 材料調整の所有保存・物理再生・新規出力への再開

H16-cの最新受入：[所有操作の条件別監査](MATERIAL_HPHI_OPERATION_ACCEPTANCE.md)。回復/最終細分を含む操作検証まで成功。H16-d GUIと親H16は未完了。以下の段階別記録は当時の範囲を示す。

最新進捗：[独立所有履歴](MATERIAL_HPHI_HISTORY.md)と[材料調整CLI/worker](MATERIAL_HPHI_TUNING_OPERATIONS.md)の基本操作検査まで成功。回復/最終細分の所有操作統合とGUIは残る。以下の初期段階の記録は当時の検査範囲を示す。

2026-09-22。H16-cの専用保存APIを実装。[材料調整runner](MATERIAL_HPHI_TUNING.md)の全元Project/nativeを所有する。独立追跡履歴、CLI/worker、実中止/管理器再起動、回復を含む操作受入はまだ残る。

`execute_material_hphi_tune(request,directory,...)`は未使用出力だけを作り、request.json、各試行のproject.jsonと専用材料native五ファイル、完了したprefixのcheckpointを保存する。各試行で元nativeを読み直し、候補Projectと照合してから物理判断を保存する。全所有ファイルと実装hashを前後で検査し、不整合な試行を完了としない。

checkpoint版1のformatは`superfish_ng_material_hphi_tune_checkpoint`、scopeは`original_material_straight_hphi_tuning`。要求・全試行・元ファイルhash・判断・回復状態を保持し、ファイル上のtrial_runsは所有ディレクトリ内の相対名。真空/曲線の保存版と混同しない。

`read_material_hphi_tune`/`replay_material_hphi_tune`は保存結果だけを信用せず、全候補を要求から再生成して、元材料nativeのRF/場/低順位スペクトルを再検証する。その元場からE/H対応、ID回復、目標/粗細判断を再計算し、保存checkpointと全量比較する。新試行をsolveするAPIではない。

再開は物理検証済みPAUSEDだけを受け取り、要求の一致を確認する。別の新規出力に全既存試行をbyte保持で複製し、自己完結したprefixを先に保存してから次試行を始める。失敗時はfailure文書と以前のcheckpointを別に保持する。元所有フォルダーやcheckpointを上書きしない。元フォルダーと全出力を移動しても、コピー元への依存を残さない。

path traversal、所有領域外への参照、symlink、余分/欠損native、要求/場/周波数改変を拒否する。材料/領域・SI/peak phasor・規格化・両R/Q/N/Aは元CaseとRFから再構成し、未対応量を0で埋めない。

## 検査と来歴

`initial.log`は新5件、123.786秒PASS/終了0。関連4件も成功し、全handle終端。検査中は製品コードを固定し、実装hashの前後一致検査を通過した。

`out/h16-material-saved-20260922/before.log`で保存API未実装のredを確認。新`test_material_hphi_tuning_saved`は実二層材料の1試行保存→別出力へ1試行再開を共通fixtureとして、次を検査する。

- 全元Case・係数・周波数・RFの保持と全trialフォルダーの所有、再生中の新試行solve禁止。
- 元フォルダーと全所有出力の移動後も、元の場所なしで再生。
- 場bytes、checkpoint周波数、format/版/型/余分キー、再開要求の改変拒否、既存出力の上書き拒否。
- solve失敗の注入後も、直前prefixを物理再生でき、未完了試行を新checkpointにしない。
- 所有外パス、checkpointとnativeのsymlink拒否。

`native-related.log`は直接利用先`test_material_hphi_saved`4件、10.185秒PASS/終了0。完全native/元場往復、途中変更、欠損/symlink、再hashされた材料場/RF/規約改変、未完了公開拒否を確認した。

既存自作所有snapshot・相対path・prefix複製の構造を、専用材料nativeと調整再検証へ接続した。新規外部資料・依存・legacy参照なし。共有solver/seed TMは変更せず、専用保存と直接利用先を検査。全suite、CLI/worker/GUI、中止/再起動の操作受入を主張しない。
