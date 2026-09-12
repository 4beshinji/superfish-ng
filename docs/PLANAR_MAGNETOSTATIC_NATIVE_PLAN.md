# S02: 平面磁静場の保存・再構築・CLI

2026-09-13 JST。固定Az付き線形磁静場を専用native/CLIへ接続する限定課題。実装中・未受入。

- Case/mesh/fields/results/manifestの5ファイルへ、全mu_r/reluctivity・Jz・境界・基準Azと元係数を保持する。
- 読込時は同じ磁静場問題を再構築/再求解し、元Az/B/H、反力/元H周回積分[A]、元Bの磁束[Wb/m]、J/mエネルギーを全再検証する。
- 保存配列・材料/源・型/基準Az/係数・規約の不整合はhash再計算済みでも拒否し、未完了/symlink/途中変更を検出する。既存出力を上書きしない。
- solve-planar-magnetostatic / replay-planar-magnetostatic / probe-planar-magnetostatic とcapabilitiesへ接続する。静電量・RFモードを混在させない。
- API/CLIの保存5ファイルとプローブ全JSONが一致し、元セル/片側のmu_r/材料情報を保持する。混在bool/領域外/--modeを拒否する。
- 独立解析済み二層・製造解・矩形電流24例で元数値/参照ファイル不変を確認し、関連unit・既存能力表・標準周波数/RFを保つ。

軸対称、Project/GUI/Study、非線形/永久磁石/異方性、巻線のインダクタンス、厳密開放境界は別工程。
新規依存・外部資料・旧版実行なし。S02と全計画は未完。
