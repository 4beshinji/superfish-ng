# H16 材料Hphi調整・保存・GUIの条件別監査

2026-09-22。原計画H16と実装分割H16-a〜dの受入条件を照合する。最後の調整回復GUI4項目、中止/再開5項目、新サーバー再生2項目、不正物理拒否5項目が分割PASS/終了0。全handle/worker/サーバー終端を確認し、以下の全条件からH16-dと親H16を受入済みとする。

| 元条件 | 直接の証拠 | 判定 |
| --- | --- | --- |
| 固定材料uniform_scaleと確認済み直線写像 | [形状則](MATERIAL_HPHI_SHAPE.md)、[細分](MATERIAL_HPHI_REFINEMENT.md)、[試行/比較空間](MATERIAL_HPHI_TUNE_TRIALS.md)。元領域/全界面、K/M移送、全加速座標、体積、折返し/予算拒否 | PASS |
| 一様材料と二層材料の実FEM調整、実最終細分 | [runner](MATERIAL_HPHI_TUNING.md)の解析TEM/二層接続式、uniform/異率伸長、最終目標と粗細差gate。guard・真縮退は別に未確認停止 | PASS |
| 材料/領域、全試行・回復、元Project/native、両R/Q/N/Aを保存 | [所有操作監査](MATERIAL_HPHI_OPERATION_ACCEPTANCE.md)。全prefixの物理再生、元移動、全bytes、hashを付け替えた改変/欠損/リンク拒否 | PASS |
| CLI/workerの実中止・新規再開・管理器再起動 | 同監査と[操作](MATERIAL_HPHI_TUNING_OPERATIONS.md)。実中止後の完成checkpointと元入力を保持し、別workerへ再開 | PASS |
| GUIの要求保持、実行/保存/再開、元場とRF | [GUI](MATERIAL_HPHI_GUI.md)、調整5項目・追跡4項目の実Chrome、全元Project/native/RF一致と場描画 | PASS |
| 独立所有履歴の明示回復、個別ID継承とGUI延長 | GUI回復履歴5項目、元未解決集合とanchor、版1/2切替、全履歴49ファイルと全要求不変 | PASS |
| 検索/最終細分の回復状態をGUIへ渡し、元場・RFを新サーバーで復元 | 材料調整回復GUI、H16-cの独立TEMで確認済み4試行TUNEDを再生 | PASS |
| GUI実中止/再開、新サーバー・新Chromeでの軸RF再生 | 真空軸・非真空材料・穴の実Chrome5項目＋再起動2項目。両R/Qと六ファイルのbyte一致を両サーバーで確認 | PASS |
| 非真空加速区間拒否、未対応損失を0で代用しない | Case/CLI拒否に加え、実Chrome5項目で非真空軸とloss_tangentを正規化/開始の両方で拒否。job非作成と有効要求の復元 | PASS |

H16-a/bのrawログを再読し、材料K/M・形状・試行・一様/二層実調整・回復の成功を確認した。H16-cの所有回復完了manifestと現在実装を比較し、差分はGUIの5ファイルのみだった（`out/h16-material-final-audit-20260922/source-audit.json`）。製品数値核・許容値・依存の変更はない。H16の対応追加は専用材料系であり、seed TMの計算経路は変更しない。

範囲は正の実数epsilon_r/mu_r、無損失・等方・区分一定の固定材料、m=0 Hphi、閉PEC、直線材料整合メッシュ。壁金属損失は既存の非磁性壁モデル、体積損失0は明示losslessモデルの結果である。有損・分散・異方・材料係数変更の調整を黙って受理しない。加速量は明示真空軸区間だけに定義し、対象外はnullと理由を保持する。

本監査は原H16カードの条件に対する分割証拠であり、全90カードの完走や全suite/リリースを意味しない。今回の追加は検証器と文書だけで、全suite/seedを再実行せず既存の対象検証を再利用した。連続体誤差上界、縮退を通る連続枝ID、未実施の外部比較を保証しない。新外部資料・依存・legacy参照なし。
