# S05: B-H・反跳材料の力・仮想仕事報告保存・CLI

2026-09-13 JST。固定856sourceを主862sourceへ統合し、専用保存API・CLI範囲で限定受入。

既存の `export_planar_magnetic_force` / `replay_planar_magnetic_force` を成功した平面B-H P1/反跳P1/P2の5ファイルnativeへ拡張した。元manifestを厳密dispatchし、元Case/係数/材料/反復履歴を実FEMで再検証する。元SHAに拘束した力/二つのトルクと、必須nullまたは実FEMの材料仮想仕事を保持する。要求version 1と線形スカラー報告version 1は変更しない。

材料報告version 2は元manifest/physicsとstatusを追加する。status=completeは処理完了を意味し、virtual_work=nullなら仮想仕事は未実施である。指定した材料仮想仕事が実求解に失敗するとstatus=virtual_work_failedとし、成功した応力、完了済みの差分/成功側、失敗Case・符号/刻み、全非線形履歴と最後の有効係数を保存する。失敗した対の差分と比較値はnull。これは精度の合格/不合格ではない。

材料の全変位Case、共回転した透磁率主軸/残留B、構成ポテンシャルと基準、J/Ht仕事と係数SHAを保持する。再読込は同じ成功/失敗を含めて実FEMと全JSONを再計算・比較する。元5ファイル、要求と報告の途中変更、誤った形式/版/物理、方向/ポテンシャル/失敗履歴の改変、リンク、上書きと出力中断を拒否する。元native外への完全JSONの非上書き公開を維持する。

CLIは既存 `analyze-planar-magnetic-force` / `replay-planar-magnetic-force` を使用し、完了0、保存・再現された実仮想仕事失敗1、不正入力/保存/改変2を返す。失敗した元nativeを成功した場として読み込むことはできない。capabilitiesは3種類の元形式、B-H P1/反跳P1/P2、報告/応力/仮想仕事の版、0/1/2とGUI未対応を明示する。

最初の対照では実際の永久磁石FEMをnativeへ保存したが、旧readerがそのmanifestを拒否した。元の失敗ログをout/planar-magnetic-force-material-native-development-20260913へ保持する。実装は元FEMや力/仮想仕事の数値計算を変更していない。

追加保存6unitと既存線形保存6unitは最初の実行で全件PASSしたが、同じコマンドで存在しないtest_capabilitiesを指定したため、集計は13件中1件のloader errorとなった（290.773秒）。正しいtest_capability_inventoryだけを追加し3件6.396秒でPASS。製品・試験コード・許容差の変更や合格12件の再実行は行わず、誤指定と補完のログを保持する。実際の検査15件が合格したことを別々に確認した。

独立20例は441.977953秒でPASS。完了12例（仮想仕事6/応力のみ6）と実変位先非線形失敗8例を、P1/P2・非線形/異方性残留磁化・回転/尺度/反転で検査した。API 2報告とCLI 1報告の全JSON/バイト一致、20抽出+40再読込+上書き/不正2+旧線形再読込8の70CLIを実行。元native 100、新報告60、要求20の180出力と44元参照ファイルが不変。旧線形24報告と元40native/要求8を含む72ファイルも不変。証拠はout/planar-magnetic-force-material-native-independent-trial-20260913/report.json。

標準はout/validation-planar-magnetic-force-material-native-candidate-20260913。受入計画は[材料保存・CLI](PLANAR_MAGNETIC_FORCE_MATERIAL_NATIVE_PLAN.md)。次の[軸方向力](OFF_AXIS_MAGNETIC_FORCE_PLAN.md)と[GUI量受渡し](S05_GUI_HANDOFF_PLAN.md)、S05/全計画は未完。原FEMや力の連続誤差保証、旧版互換、ホストCI実行とは扱わない。新規依存・外部資料・旧版実行なし。

標準3190.289秒、1365合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは172.535秒でPASS。標準/独立の固定856sourceと主862source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
