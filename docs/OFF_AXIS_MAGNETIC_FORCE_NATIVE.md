# S05: 軸を含まない磁気力報告の保存・CLI

2026-09-13 JST。固定863sourceを主869sourceへ統合し、専用API範囲で限定受入。

専用 `export_off_axis_magnetic_force` / `replay_off_axis_magnetic_force` は、成功した線形スカラー正半径P1/P2 native 5ファイルを元FEMで照合し、全周の軸方向力Fz[N]と任意の実変位仮想仕事[J/N]を保存・再計算する。元ψ基準/係数、全Case、対象とP1重み、元求積/+4診断を保持する。平面N/m、半径方向の正味ベクトル力、断面回転トルクへ読み替えない。

専用request/report version 1を厳密にparseする。要求は対象region IDs、P1重み、必須virtual_work=nullまたはtranslation_steps_m（正・厳密減少・2..8個）。原点や回転要求は未知フィールドとして拒否する。nullでは仮想仕事と応力比較もnull。指定した仕事は全±z変位Case、固定r/外部境界、積分電流[A]、ポテンシャル/エネルギー/源境界仕事[J]と係数SHAを含む。差分・求積の診断は連続誤差上界ではない。

完全JSONを元native外へ一時作成し、非上書き公開する。再読込は明示元nativeのSHAと同じ実FEMの全JSONを照合する。単位/ψ/求積/Case/ポテンシャルの改変、元/要求/報告の途中変更、リンク、異なる物理、上書き、中断を拒否する。CLIは `analyze-off-axis-magnetic-force RUN --request REQUEST --out REPORT` と `replay-off-axis-magnetic-force RUN REPORT`、完了0/不正・保存エラー2。capabilitiesに全周N/JとP1/P2、正半径・線形限定を明示する。

追加保存6unitとcapability 3unitは84.609秒でPASS。独立20例は367.082222秒でPASS。両要素次数、電流/外部磁場反転、尺度、mu_r=3/7の対象、q=4/32、ψ基準変更を含む。仮想仕事10/応力のみ10、API 2報告とCLI 1報告の全JSON/バイトが一致。20抽出+40再読込+上書き/不正2の62CLIを実行。元native 100、新報告60、要求20の180ファイルと元参照50ファイルが不変。

独立証拠はout/off-axis-magnetic-force-native-independent-trial-20260913/report.json、標準はout/validation-off-axis-magnetic-force-native-candidate-20260913。受入計画は[保存・CLI](OFF_AXIS_MAGNETIC_FORCE_NATIVE_PLAN.md)。次の[GUI量受渡し](S05_GUI_HANDOFF_PLAN.md)、軸接続/B-H/反跳の軸対称力とS05/全計画は未完。新規依存・外部資料・旧版実行なし。

標準3267.081秒、1377合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは76.142秒でPASS。標準/独立の固定863sourceと主869source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
