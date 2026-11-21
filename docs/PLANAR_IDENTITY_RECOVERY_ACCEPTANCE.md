# 開発カードP02 — 平面個別ID回復の条件別受入

2026-09-22、実装開始P01後から `a14cf18` のGUI接続までを監査し、P02-a〜dと開発カードP02を受入。
これは互換計画の平面形状全体やD02全体の完了ではない。非線形写像P03/P04、曲線P2など後続カードと原90カードのgoalは継続する。

| 明示条件 | 現在の証拠と結論 |
| --- | --- |
| 完全比較・過去個別ID・全継承集合による回復 | [核](PLANAR_IDENTITY_RECOVERY.md)。継承/anchorを元FEMから再計算、集合外ID拒否。PASS |
| 真正方形と矩形順位交換の独立対照 | 同文書の独立c/(2w), c/(2h)と元E正弦相関。真縮退/guard未確認では回復周波数null。PASS |
| 元場/周波数・RFを改変しない | 核の元配列不変、[P01尺度則](PLANAR_AFFINE_TUNING.md)、所有履歴hash、GUI取込全native/Project bytes一致。PASS |
| anchorの過去解決位置への束縛 | [所有履歴](PLANAR_RECOVERED_HISTORY.md)。誤位置/置換ID/再hash改変拒否、移動後再生。PASS |
| 履歴・CLI・workerで回復後の継承 | 所有履歴の実CLI/worker回復→延長。mode-2/mode-1、元null保持、管理器再起動。PASS |
| 調整検索と最終細分・別job再開 | [調整受入](PLANAR_TUNING_RECOVERY.md)。固定/最新anchor、矩形/多項式版3、両gate、回復失敗で周波数null停止。PASS |
| 旧形式維持とstrict入力 | 版1/2調整、版1履歴を保持。関連14件、GUI既存4件、重複/未知キー拒否。PASS |
| 実GUI履歴回復→延長・同順位/ID | [GUI記録](PLANAR_RECOVERY_GUI.md)の実Chrome15項目。mode-2/mode-1、元集合null、後続実比較/延長。PASS |
| 実GUI調整回復→最終細分 | Chrome14項目中、検索/細分で元集合null・採用x/y、対象順位2→1、独立した最終目標/粗細gate。PASS |
| 実取消し・再開・新サーバー元場表示 | 14項目中の実中止checkpoint検証/新job再開、新サーバーの5項目でTUNED回復再生/元場描画/未確認非採用。PASS |
| 元native/Project bytes | 履歴native-import-audit.jsonは5ファイル、調整native-project-audit.jsonはProject+nativeの6ファイル一致。全調整祖先hash保持。PASS |

GUI証拠は `out/p02-planar-history-browser-20260922/` と `out/p02-planar-tune-browser-20260922/`。
各report.jsonのPASS項目、実行時389製品ファイルhash不変、外部HTTP要求0を監査時の現行ファイルと再照合した。
履歴session 91632、調整/新サーバーsession 87997はいずれも終了0。Chrome/サーバー/管理器の終了処理まで完了。
履歴・調整の画面PNGも目視確認した。URL再読込と新サーバー起動を別の証拠として区別する。

P02-aの初回テスト期待文不一致、P02-bの版8保存入口欠落、P02-dの版8フォーム欠落は各専用文書の再現/修正記録を保持した。
それらを初回から成功した検査とは扱わない。既存成功証拠の数値核と、最後のGUI/検証スクリプト差分を区別した。
本受入は専用核・所有履歴・調整・直接利用先・実GUIの分割検証であり、全suiteやseed validatorを実施したという主張ではない。
FEM/seed TM/材料核はこの回復接続で変更しておらず、影響は平面回復経路に限定した。
新しい外部数学資料・依存・旧版ソース/バイナリ参照はない。

回復は宣言した過去場への再同定であり、縮退点を通る物理枝の連続証明ではない。
調整の粗細差は誤差上界ではない。調整checkpointは既存の絶対パス祖先参照、所有履歴は元nativeコピーという異なる保存契約を保持する。
