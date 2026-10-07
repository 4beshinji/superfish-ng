# N06：新規一様FEMと元ID・RF/離散peak確認

2026-10-08 JST：下記別ツリーの受入temp commitf5eaf4bと全1210 Python源の一致を
確認し、新module/testを主へ同byteで統合した。元1415対象源は不変、新1417対象源。
新5個別unitの分割証拠を再利用し、統合だけのunit/FEM/seed/full/12benchmark再実行は0。
rawは `uniform-worker-acceptance.json` と `uniform-worker-main-integration.json`。
以下の「主への統合は後続」は限定受入時点の履歴である。

2026-10-08 JST、N06一様workerの限定受入。N06はIN_PROGRESS。
先行は[N05の固定比較条件](N05_ADAPTIVE_EFFICIENCY_PLAN.md)、
[N06の同一初期入力](N06_FIXED_EXECUTION_PLAN.md)と[費用記録器](N06_EFFICIENCY_TIMING.md)。
主ではN03全validate/seed207量が終端し、元1405源不変を確認した。
実装/開発検査は `/tmp/superfish-ng-n06-uniform-worker-20261008` で行った。

`adaptive_efficiency_uniform.execute_uniform_efficiency` は元P2 Case/初期meshから
毎回実FEMを行う。解析参照や別反復のnativeをsolveの代わりにしない。
全要素4分割だけを使用し、局所mark/選択を実行しない。
affine版3/曲線版4の既存strict要求を読み、閉PEC・軸接続真空m=0 TM P2と
新規初期幾何だけを受け付ける。TE/未対応入力を求解前に拒否する。

直線は全markedを既存refine_marked_cellsへ渡す。曲線は元source mesh/P2境界を保ち、
元均等restrictionとCaseのuniform水準から求解する。解析境界へ再投影しない。
保存完了/再構築後に実Hφのnested_affine/nested_curved個別IDを追跡し、
未解決なら量を評価せず停止する。元スペクトル・規格化・符号を保つ。
f・両R/Q・Gと離散E/B peak比の上下界について、連続二変化を別に確認する。
曲線では元indicator/formの12/24求積差も確認し、選択費用とは名付けない。
原max_levels/Case要素上限/最小角と追跡feature上限を保つ。

TARGETS_METはnative量の二変化だけ。独立物理精度の状態はNOT_RUN、誤差上界はnull。
max_new_levelsの開発分割はPAUSED、最終水準上限はLEVEL_LIMIT、要素不足は
次のsolve前にREFINEMENT_LIMITとして保存する。主実行器の壁時計/RSS予算は別に接続する。
全native/各checkpoint・結果・元失敗型を新directoryへ保存し、実装と元nativeの
hashを各水準後に再検査する。元例外/中断を再送出し、既存出力は起動前に拒否する。
この最初のworkerにresume API/独立参照判定/12実比較が完成したとはしない。

段階は初期mesh/品質、均等細分、solve/規格化、RF/save、native再構築、
元個別ID、離散peak、求積indicator/form、二変化、checkpoint保存を実観測できる。
組立/固有値など内側のalias接続とprocess/importの外側費用は後続。
一様に実施していない局所選択の架空秒を足さない。

## 独立不変量と検査

新5個別unitを分割受入した。円筒P2の実40/160/640三水準で、周波数誤差と
全域Er/Ez/HφのBessel解に対する差が減少することを確認。
元U=1 J、共通単一符号、両R/Q factor2、全壁lossを含む最終f1e-4/場・RF0.005を確認した。
場の振幅fitや一部の場点の削除はしない。
球の実三水準で元source mesh/P2境界の係数距離、Ritz、全個別ID/12・24求積差を確認し、
元SphereTMの根条件からf1e-4/両R/Q・G・全壁loss0.005を確認した。
これらは開発不変量であり、N05の各二反復/全域場・peakの実比較の代替ではない。

未実装moduleのImportErrorをbaselineとして保全。
初稿4件1.331秒は円筒/元solver失敗/未対応物理の3件PASS、要素上限1件は
検査側で完了marker名をcomplete.jsonと仮定してFAILだった。
既存read_solutionによる全保存検査へ訂正し、必要な予算停止と新球2件だけを実行。
8.828秒で予算停止PASS、球は境界certificateにstatusキーを仮定した検査側KeyError。
元係数距離/元許容差と区間数を検査するよう訂正し、球1件だけ8.701秒・終了0でPASS。
元solver/数値源を変えず、通過済み円筒/他の検査を再実行しない。
これらの三実行は開発FEM計11回で、12benchmarkは0。元FAIL/ERRORと費用はraw logに残す。
unitのnativeは通常のTemporaryDirectory内の開発成果物で、固定比較の保存証拠ではない。

tempの明示PYTHONPATH/主uv環境で `python -m unittest -v` の対象を上記の順に選んだ。
元1208 Python源と主1415対象源は不変、temp1210 Python源/全1411点
（主の生成egg-info六点なし）を確認する。
rawは `out/n06-cost-recording-20261007/uniform-worker-*.log` と
`uniform-worker-acceptance.json`。new seed/full/legacy実行0。
主への同byte統合、独立参照評価と元保存の再生/均等・適応の実worker比較は後続。
N06/親N04/全goalは継続する。
