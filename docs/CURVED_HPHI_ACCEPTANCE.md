# H13 曲線Hφの履歴・調整：条件別監査

2026-09-22受入。原カードとH13-a〜eの全条件を下表で照合した。HTTP転送上限の実不具合、失敗した操作と修正後の補完を分割証拠として明示し、原範囲を縮小していない。

| 原カードの条件 | 証拠 | 状態 |
|---|---|---|
| 曲線変形の全元Project・係数・穴・加速座標を保持 | [形状則](CURVED_HPHI_SHAPE.md)、[試行/同P2最終細分](CURVED_HPHI_TUNE_TRIALS.md)、[所有保存](CURVED_HPHI_TUNING_SAVED.md)。元二次領域から細分し、軸端点/位相原点を明示移送 | H13-a/c/d受入済み |
| 元E/H・scalar・有限比較スペクトルで追跡 | [追跡核の条件別監査](CURVED_HPHI_TRACKING.md)。独立TEM場・解析縮退・順位交換・guard停止を分離 | H13-b受入済み |
| 実曲線穴付きFEM調整 | [調整核](CURVED_HPHI_TUNING.md)。非一様穴付き調整は目標/粗細差を別判定。粗い例のREFINEMENT_FAILEDを成功に置換しない | H13-c受入済み |
| CLI/worker/所有履歴と明示anchor回復 | [履歴](CURVED_HPHI_HISTORY.md)、[調整回復の所有操作](CURVED_HPHI_TUNING_RECOVERY_SAVED.md)。回復済みIDだけを次へ継承 | H13-d受入済み |
| 曲線追跡/履歴GUIとAPI全native/RF一致 | [GUI](CURVED_HPHI_GUI.md)。曲線比較/履歴worker、元Project単位と元場/RFの一致、Chrome4項目。元12ファイル不変 | 第一段階受入済み |
| 曲線調整GUIとAPI全native/RF一致 | [GUI](CURVED_HPHI_GUI.md)。完全要求、保存再読込、別job再開、元場描画のChrome5項目。元12ファイル不変 | 第一段階受入済み |
| 穴付き曲線で実中止/保存地点再開/元場再表示 | `out/h13-curved-hole-cancel-gui-20260922/`の実Chrome/worker操作 | 実中止/再開後、HTTP上限不備を修正して新サーバー/Chromeで元場を再検査。native-auditで元Project/native6ファイルbyte一致、取消prefix/再開prefix6ファイル一致・穴1個・現行hash一致、全handle終端 |
| 調整と履歴の明示回復GUI | `out/h13-curved-recovery-gui-20260922/`と`out/h13-curved-history-recovery-gui-20260922/` | 履歴5項目、調整4項目PASS。全handle終端、回復調整の元24ファイル不変/取込先6ファイル一致。履歴の所有49ファイル不変 |
| サーバー再起動後の復元 | 回復調整の最初のHTTP 200/正常終了、新サーバー/新Chromeを記録 | 穴付き再開と回復調整の新サーバー/新Chrome復元・全元場byte一致・正常終了まで確認済み |
| 旧直線/同領域の保存版読み込み | H13-d各旧保存/CLI/worker回帰、GUIの`test_gui_hphi_tuning`、`test_gui_hphi_tracking`、旧履歴延長ケースを分割検証 | 既存証拠を保持。全suite実施とはしない |

FEM/形状/求積/許容値をGUI受入のために変更していない。製品の数値核はH13-a〜dの独立物理受入と分離する。新規依存・外部資料・legacy参照なし。GUI操作検査の全終端と元データ/実装hashの照合を確認し、H13-eと親H13を受入とする。H14仕様は既に受入済み。次はH15-aの固定材料領域/界面比較。全計画goalは継続。
