# P04: 材料Hφの専用保存・再生・CLI

2026-09-13 JST。材料Hφの固有解/場/RF APIに続く限定課題。未受入。
既存専用native方式を材料Case版1へ接続し、材料分割・元セル・係数・RFを再検証して保存/再生する。

受入条件：

- case.json、mesh.npz、fields.npz、results.json、最後にmanifest.jsonを公開する。既存出力を上書きしない。
- 全材料/領域/界面/元メッシュとP1/P2 DOFを保持し、材料係数・界面所有・規格化・最低正スペクトル・領域RFを再構築する。
- 内容hashを作り直した材料/幾何/場/順位/RF/規約の改変も拒否する。リンク、欠落、検証中変更を拒否する。
- solve-material-hphi、replay-material-hphi、probe-material-hphiを専用入口として実装する。
- SIプローブに片側セル・領域/材料・epsilon_r/mu_r、E/H/Bの全18成分と規約を保存する。Bを真空のmu0 Hへ戻さない。
- API/CLIでnative全5ファイルが一致し、プローブ値/材料メタデータ・元ファイル不変、低帯域/真空経路/尺度則を照合する。
- 能力情報は専用材料入口の受入済み範囲を記載し、canonical Modelや既存真空Caseの受理を変更しない。
- 全標準回帰と既存の周波数/RFを保つ。Project/GUI/Studyは後続で実worker・保存復元まで独立に受け入れる。

新規外部資料・依存・旧版参照なし。旧版材料入力互換とP04全体の受入は含めない。
