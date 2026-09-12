# S02: 軸非接続の磁静保存・再構築・CLI

2026-09-13 JST。[実装記録](OFF_AXIS_MAGNETOSTATIC_NATIVE.md)の専用API範囲で限定受入。

mu_r/reluctivity・Jphi・全境界/穴・自由DOFと荷重、基準psiと相対/絶対psiを5ファイルへ保存する。再読込は同じ実FEMを再求解し、全配列・元6場・Jエネルギー/Wb磁束/A電流・反力と物理規約を照合する。定数psiの零場を保持し、Aphi=C/rを一様Bへ読み替えない。

solve-off-axis-magnetostatic、replay-off-axis-magnetostatic、probe-off-axis-magnetostaticの3CLIと能力表を接続する。保存の上書き・リンク・未完了・検査中変更・再hash後の物理/係数/規約改変を拒否する。manifestを最後に公開する。

追加4unit/既存能力表テスト、独立解析済み24例で48native・80CLIを検査する。一様B8、粗い環状電流8、二層8を選び、API/CLIの5ファイル・全プローブJSON・元240native/90参照ファイルの不変を確認する。零場と基準は追加unitでもP1/P2を確認する。標準周波数/RFは別に維持する。

Project/GUI/StudyはO02の後続。軸が領域外の絶対磁束・巻線インダクタンス・純Ht・厳密開放境界は主張しない。S02/全計画は未完。
