# 軸接続磁静の専用保存・再構築・CLI

2026-09-13 JST。[計画](AXIS_MAGNETOSTATIC_NATIVE_PLAN.md)の固定731sourceを主737sourceへ統合し、専用API範囲で限定受入。
候補は `/tmp/superfish-axis-magnetostatic-native-20260913`。

Case/mesh/fields/results/manifestの5ファイルへ、mu_r/reluctivity、Jphiと源仕事荷重[A m²]、全境界/軸/領域所有、全軸DOF、元a=Aphi/r[T]係数を保持する。aの定数はgaugeではないため、基準移動しない。同じ問題の再求解で固定境界・自由DOF残差・全配列・元6場・物理量・SI規約を再検証する。

元a/Aphi/Br/Bz/Hr/Hz、全回転体エネルギー[J]、磁束[Wb]、電流[A]と固定a反力[A m²]を区別する。プローブには軸のAphi=Br=0、片側mu_r/領域/材料・保存元hashを保持する。保存は既存出力を上書きせずmanifestを最後に公開し、未完了・symlink・途中変更・hash再計算済みの改変を拒否する。

`solve-axis-magnetostatic CASE --out RUN`、`replay-axis-magnetostatic RUN`、`probe-axis-magnetostatic RUN --points POINTS --out JSON`を接続した。`--mode`を受け付けず、capabilitiesには軸接続の正則空間、全外周Htも可能な境界条件、物理量と除外を明示する。

追加4unitが11.321秒でPASS。既存能力表3unitと3CLI smokeもPASSし、API/CLIの保存5ファイルがbyte一致、全プローブJSONが一致した。独立解析88例のうち一様B8・円筒電流8・二層8の24例で48native/80CLIがPASS。標準1191件は `out/validation-axis-magnetostatic-native-candidate-20260913` へ終了0。

軸非接続、Project/GUI/Study、非線形/永久磁石/異方性、巻線インダクタンスと厳密開放境界は未接続。新規依存・外部資料・旧版実行なし。S02と全計画は未完。

独立24例は465.244秒でPASS。
標準2323.604秒、1188合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは10.892秒でPASS。731sourceと主737source（不変egg-info 6件）は完全一致。独立例は候補hashに結び付け、本体で同じ全例を再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
