# 平面磁静場の専用保存・再構築・CLI

2026-09-13 JST。[計画](PLANAR_MAGNETOSTATIC_NATIVE_PLAN.md)の固定718sourceを主724sourceへ統合し、専用native/CLI範囲で限定受入。
候補は `/tmp/superfish-planar-magnetostatic-native-20260913`。

専用Case/mesh/fields/results/manifestの5ファイルに、mu_r/reluctivity、領域/境界所有、Jzからの荷重[A]、基準Az[Wb/m]と相対/絶対係数を保持する。保存前・再読込時は同じCaseから再求解し、固定Azと自由DOF、全配列、元Az/B/H、J/mエネルギー、反力/元H周回積分、B磁束、SI規約を再照合する。静電容量や巻線インダクタンスは推定しない。

保存は既存出力を上書きせず、検証後にmanifestを最後に公開する。未完了、symlink、途中変更、hashを再計算した材料/係数/源/境界/量/規約の改変を拒否する。プローブは元セルの片側mu_r・領域・材料・Az/B/Hと保存元hashを保持し、native外へ出力する。

`solve-planar-magnetostatic CASE --out RUN`、`replay-planar-magnetostatic RUN`、`probe-planar-magnetostatic RUN --points POINTS --out JSON`を接続した。`--mode`は受け付けない。`capabilities`は専用形式と物理量、明示境界、対応範囲を返す。

新規4unitが4.548秒でPASS。既存能力表3unitと3CLI smokeもPASSし、API/CLIの保存5ファイルがbyte一致、全プローブJSONが一致した。独立解析88例のうち二層8・製造解8・矩形電流8の24例で48native/80CLIがPASS。標準1176件は `out/validation-planar-magnetostatic-native-candidate-20260913` へ終了0。

軸対称、Project/GUI/Study、非線形/永久磁石/異方性、巻線インダクタンスと厳密開放境界は未接続。新規依存・外部資料・旧版実行なし。S02と全計画は未完。

独立24例は195.902秒でPASS。元240native/90参照ファイルのhash不変を照合した。標準2286.619秒、1173合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは4.558秒でPASS。718sourceと主724source（不変egg-info 6件）は完全一致。独立24例/80CLIは候補hashに結び付け、本体で同じ全例を再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
