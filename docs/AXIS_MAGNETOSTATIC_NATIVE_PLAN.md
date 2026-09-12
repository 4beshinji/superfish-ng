# S02: 軸接続磁静の専用保存・再構築・CLI

2026-09-13 JST。正則a=Aphi/rの実FEMを専用native/CLIへ接続する限定課題。[実装記録](AXIS_MAGNETOSTATIC_NATIVE.md)の専用API範囲で限定受入。

- Case/mesh/fields/results/manifestの5ファイルへ、全mu_r/reluctivity、Jphi、軸/固定Aphi/r/Ht境界、軸DOFと元a[T]係数を保持する。定数aをgauge移動しない。
- 同じ磁静問題を再求解し、元a/Aphi/Br/Bz/Hr/Hzと全回転体のエネルギー[J]・磁束[Wb]、電流[A]、固定aの反力[A m²]を単位・向きの規約ごと検証する。
- hash再計算済みの材料/荷重/軸/係数/規約改変、不完全、symlink、途中変更を拒否する。既存出力を上書きしない。
- solve-axis-magnetostatic / replay-axis-magnetostatic / probe-axis-magnetostaticを追加し、capabilitiesへ軸接続範囲と除外を明示する。--modeは受け付けない。
- 独立解析済み一様B8・円筒電流8（穴を含む）・二層8の24例で48native/80CLIを照合する。API/CLIの5ファイルbyte一致と全プローブJSON一致、軸の正則値、片側mu_r/材料、元native/参照ファイル不変を要求する。
- 関連unit、既存能力表、標準周波数/RFを保持する。

軸非接続・Project/GUI/Study・非線形/永久磁石/異方性・巻線インダクタンス・厳密開放境界は別工程。新規依存・外部資料・旧版実行なし。S02と全計画は未完。
