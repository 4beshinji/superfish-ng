# H16-c 所有保存・履歴・CLI/workerの受入監査

2026-09-22。元H16の条件をa〜dへ分割したうち、H16-cのみを対象とする。H16-dのGUIと親H16の統合受入は未完了。最後の所有回復/軸RF操作検査2件が601.458秒PASS/終了0となり、全handle/worker終端を確認した。以下の全条件を満たしたためH16-cを受入済みとする。

| 条件 | 実装・直接の検証証拠 | 状態 |
| --- | --- | --- |
| 全材料Project/native/試行を所有し、元表示単位・RF・規格化を保持 | [材料調整保存](MATERIAL_HPHI_TUNING_SAVED.md)、保存新5件とnative関連4件 | PASS |
| 移動後の物理再生、別出力へのprefix再開、失敗前の完成checkpoint保持 | 保存検査と[CLI/worker](MATERIAL_HPHI_TUNING_OPERATIONS.md)の実再開・移動・注入失敗 | PASS |
| 材料二状態追跡の所有、元Caseと全比較宣言の照合、実worker/CLI | [材料追跡ジョブ](MATERIAL_HPHI_TRACKING_JOBS.md)新4件と関連2件 | PASS |
| 独立追跡履歴、全native連続性、未解決ID集合継承、明示過去anchor回復 | [材料履歴](MATERIAL_HPHI_HISTORY.md)新4件と関連2件。TEM場、guard拒否、実worker延長・再起動 | PASS |
| 実中止からの新規再開、管理器再起動、全prefix/入力/manifest改変拒否 | 材料調整CLI/worker新8件307.737秒、旧CLI関連1件70.743秒 | PASS |
| 回復済み調整から実最終細分へ再開し、元全試行・回復状態・RFを保持 | [所有回復検査](MATERIAL_HPHI_OWNED_RECOVERY.md)、CLI検索→worker細分→元移動→管理器再起動→全物理再生 | PASS |
| 材料/領域、両R/Q/N/A、真空軸区間と未対応損失の拒否を操作経路で保持 | 同検査の真空軸＋非真空材料＋穴Project保存/再import、非真空加速区間とloss_tangent拒否 | PASS |

材料そのものの周波数・場・RFの独立検証は[H15受入](MATERIAL_HPHI_ACCEPTANCE.md)に、固定材料変形/細分は[候補・比較空間](MATERIAL_HPHI_TUNE_TRIALS.md)に、実一様/二層調整・独立解析目標・粗細gate・真縮退拒否は[H16-b](MATERIAL_HPHI_TUNING.md)に分離する。今回の保存/操作検査だけで連続体精度や連続経路の枝IDを保証しない。

lossless材料の体積損失0は明示した物理モデルの値であり、未対応の有損材料を0で代用してよいという意味ではない。加速区間なしの両R/Qはnullと理由を保持し、真空軸区間がある場合だけ二つの定義を返す。

新規の製品数値核・許容値・依存変更なし。元Project/native/回復を所有する操作契約の検証であり、全suite/seed・実GUIクリックは今回の監査に含めない。各記録の対象コマンド・終了状態を参照し、過去の部分実行を全受入へ読み替えない。
