# 明示曲線Hφのnative・CLI

[専用FEM/RF API](CURVED_HPHI_RF_PLAN.md)に続く保存工程。[実装記録](CURVED_HPHI_NATIVE.md)の範囲で限定受入。
既存native形式とは区別した専用schema 1で、case/mesh/fields/resultsと最後に公開するmanifestの5ファイルを保存する。

受入条件：

- 二次幾何の元頂点・全中点・セル/境界接続、全穴/軸/区間、P1/P2 DOF、元係数・最低正周波数、q/u・零空間・phasor・U・両R/Qを保持する。
- 公開前と読込時に元幾何/K/M・最低正スペクトル・全場由来のRFを再検証する。未知配列/型/形式、リンク、不完了、再hashした幾何・係数・RF・規約の改変、読込中の変更を拒否する。
- 元入力と整合しない解は新しい出力先を作る前に拒否する。既存出力を上書きせず、完成manifestを最後に公開する。
- 専用CLIでsolve/replay/probeを実行し、全E/H/B成分と規約を新しいJSONへ出す。穴/領域外は拒否し、プローブ先をnative内へ作らない。
- 軸あり/なし・穴・曲線・P1/P2・複数尺度の独立FEM/RF・保存往復・実CLIを照合する。元入力/nativeの不変と標準f/RFを確認する。

Project・Job・GUI・Study・追跡への統合は後続。既存の保存共通処理とCLIを再利用し、新規外部資料・依存・旧版参照は予定しない。

標準1099件、関連30unit、独立24ケース/48保存/74CLIと主4unit/同照合、追加半径非線形24ケースがPASS。主659sourceへ統合済み。
