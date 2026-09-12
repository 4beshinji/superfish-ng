# S01: 平面静電の保存・再構築・CLI

2026-09-13 JST。平面静電の実FEM結果を、中立Cartesian幾何・単位長さの静電量を保持した専用nativeへ接続する限定課題。実装中・未受入。

受入条件：

- Case/mesh/fields/results/manifestの5ファイルへ全材料/rho/境界・基準電位・元係数を保持し、完了manifestは最後に発行する。既存出力を上書きしない。
- 読込時にCaseから同じPoisson問題を再構築/再求解し、元係数・全配列・反力/元場電荷・J/mエネルギー・F/m容量・規約を再検証する。
- 異なる材料/電荷/境界、係数・型・基準電位・単位の不整合はhash再計算済みでも拒否する。未完了・symlink・読込/発行中の変更も検出する。
- solve-planar-electrostatic / replay-planar-electrostatic / probe-planar-electrostatic とcapabilitiesへ接続する。モード番号とRF規約を持ち込まない。
- API/CLIのnative5ファイルとプローブ全JSONが一致し、元セルのPhi/Ex/Ey/Dx/Dy・片側材料情報を保持する。混在bool/領域外入力は出力作成前に拒否する。
- 独立解析で照合した二層、凹形/回転製造解、矩形電荷問題を保存再生し、元数値と参照ファイルの不変を確認する。
- 関連unit・CLI拒否・既存能力表・標準周波数/RF回帰を保つ。Project/GUI/Study・純Neumann・浮遊電極・外部境界診断は別工程。

新規依存・外部資料・旧版実行なし。S01と全計画は未完。
