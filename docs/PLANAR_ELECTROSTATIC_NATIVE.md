# 平面静電の専用保存・再構築・CLI

2026-09-13 JST。[計画](PLANAR_ELECTROSTATIC_NATIVE_PLAN.md)に従う固定700sourceを主706sourceへ統合し、専用native/CLI範囲で限定受入。
候補は `/tmp/superfish-planar-electrostatic-native-refined-20260913`。

専用Case/mesh/fields/results/manifestの5ファイルへ、中立Cartesian幾何、誘電体/界面/領域、全rho/境界、DOF、体積/境界荷重[C/m]、基準電位と相対/絶対係数を保持する。
エネルギーはJ/m、電荷はC/m、容量はF/mで、回転体積・軸DOF・RFモードやphasorを持ち込まない。

読込時はCaseから固定電極付きPoisson問題を実際に再構築/再求解する。元係数の型/次元/基準電位/固定電極、再構築解と自由DOF残差を検査し、元配列とPhi/E/D・電荷/エネルギー/容量・規約を全再生する。
内容hashの再計算だけでは不整合を通さない。発行前の入力変更、未完了出力、symlink、読込中の変更を拒否する。
manifestは最後に発行し、既存出力は上書きしない。

`solve-planar-electrostatic CASE --out DIR`、`replay-planar-electrostatic DIR`、`probe-planar-electrostatic DIR --points XY_JSON --out JSON` を追加する。
プローブは元セルのPhi/Ex/Ey/Dx/Dy、片側の材料/領域とepsilon_rを返す。領域外・混在boolは出力作成前に拒否する。capabilitiesに形式・SI単位・制約を列挙する。

追加4unitは4.424秒、既存能力表3unitは5.958秒でPASS。3コマンドのsmokeでAPI/CLIの5ファイルbyte一致も確認した。
独立解析88例の最終PASS後、二層8・製造解8・矩形源問題8の計24例48native/80CLIを保存再生しPASS。
標準1159件は `out/validation-planar-electrostatic-native-candidate-20260913` へ終了0。
独立照合は `out/planar-electrostatic-native-independent-20260913/report.json`。API/CLIの5ファイルとプローブ全JSONが一致し、元240nativeと参照ファイルは不変。

Project/GUI/Study、純Neumann/浮遊電極、曲線/穴、外部境界の遠方化診断は別工程。
新規依存・外部資料・旧版実行なし。S01と全計画は未完。

独立24例/80CLIは193.876秒、標準2268.858秒、1156合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは4.335秒でPASS。参照90ファイルも不変。
固定候補700sourceと主706source（不変egg-info 6件）を完全照合した。24例/80CLIの独立証拠は候補source hashへ結び付け、本体で同じ全例を再実行したとは扱わない。標準実行の固定候補との差は独立物理検証スクリプトのP2最細n64→80だけで、製品・テスト・例・他スクリプトは完全一致。標準1159件を再実行したとは扱わない。旧ベンチマークと許容差は不変。統合証拠は標準出力内seed_regression.json。
