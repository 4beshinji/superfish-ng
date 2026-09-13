# S05: 平面磁場の力・トルク報告保存・CLI

2026-09-13 JST。固定848sourceを主854sourceへ統合し、専用保存API・CLI範囲で限定受入。

専用API `export_planar_magnetic_force(run,out,request)` と `replay_planar_magnetic_force(run,report)`。元データは線形スカラーP1/P2の成功native 5ファイルに限る。力/トルクの[元API規約](PLANAR_MAGNETIC_FORCE.md)を維持し、元FEM再求解、元5ファイルSHA、Case・絶対/相対Azの一致で拘束する。

要求 `superfish_ng_planar_magnetic_force_request` version 1 は明示body_region_ids、全節点weights、原点origin_xy_mと、必須virtual_workを持つ。virtual_workはnull（応力のみ）、または2..8個ずつの正で厳密減少するtranslation_steps_m/rotation_steps_radである。未知キー、bool/複素数/非有限数、重複領域、誤った重み/刻みを拒否する。暗黙の仮想仕事や磁石長を導入しない。

報告 `superfish_ng_planar_magnetic_force_report` version 1 は要求、元5ファイルSHA、力/重み付きトルク/節点回転応力トルクの完全報告、nullまたは全±変位Case/停留ポテンシャル/エネルギー/源境界仕事/係数SHAと差分系列を保持する。応力と仮想仕事の比較は実際の節点移動に対応する節点回転トルクを明示して使う。数値差を保持し、精度合格boolや自動許容差を製品報告へ持ち込まない。

CLIは `analyze-planar-magnetic-force RUN --request REQUEST --out REPORT` と `replay-planar-magnetic-force RUN REPORT`。成功0、不正入力・上書き・元データ不整合・I/O失敗2。元native外へ完全な一時JSONを作成して非上書き公開する。元/要求/報告の途中改変、シンボリックリンク、非通常ファイルを拒否し、報告の全JSONを再計算して比較する。boolと整数のすり替えも拒否する。

追加6unitとcapability 3unitは123.586秒でPASS。P1/P2・単電流/偶力・線形材料bodyと仮想仕事あり/なしを検証した。力と二つのトルク、重み、変位Case、停留ポテンシャル、比較の単位、版の改変を拒否し、出力中断/間違った元データも検査した。

独立8例（仮想仕事4、応力のみ4）は151.277446秒でPASS。API 2報告とCLI 1報告を各例で比較し、24報告の全JSONとバイトが一致。8抽出、16再読込、上書き/不正要求2件の計26CLIを実行した。元native 40ファイル、24報告、8要求の計72出力と、元物理対照24ファイルが不変。証拠は `out/planar-magnetic-force-native-independent-trial-20260913/report.json`。固定候補のfingerprintに拘束する。

標準検証出力は `out/validation-planar-magnetic-force-native-candidate-20260913`。受入計画は[保存・CLI計画](PLANAR_MAGNETIC_FORCE_NATIVE_PLAN.md)。B-H/反跳材料力は[次の独立計画](PLANAR_MAGNETIC_FORCE_MATERIALS_PLAN.md)、材料仮想仕事・GUI・軸対称とS05全体は未完。原FEMの精度保証、旧版互換の証明、ホストCIの実行とは扱わない。新規依存・旧版実行なし。

標準2915.122秒、1347合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは118.495秒でPASS。標準/独立の固定848sourceと主854source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
