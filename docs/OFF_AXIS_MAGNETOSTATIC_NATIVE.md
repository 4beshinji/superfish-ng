# S02: 軸非接続の磁静保存・再構築・CLI

2026-09-13 JST。固定749sourceを主755sourceへ統合し、専用API範囲で限定受入。

[限定計画](OFF_AXIS_MAGNETOSTATIC_NATIVE_PLAN.md)の5ファイルnativeと3CLIを実装した。mesh.npzは全mu_r/reluctivity・領域・境界成分/穴・DOF・荷重A・面積/体積を保持し、fields.npzはreference_psi_wb、psi_relative_to_reference_wb、psi_wbの有限float64を持つ。同じ固定psi/Htの実FEMを再求解し、全配列と元6場・J/Wb/Aの全量・規約を照合する。

結果は域内の磁束差と定数psiの参照自由度を明示する。定数psiの零場とAphi=C/rを保持し、領域外の軸を貫く絶対磁束を推定しない。能力表のProject/GUI/Studyはfalse。CLIにモード番号やRF phasorはない。

追加4unitは20.060秒でPASS。既存能力表3unit、3CLIの実スモークもPASSし、API/CLIの5ファイルがバイト一致、全プローブJSONも一致した。零場P1/P2、二層/穴、基準・全元場、再hash後の物性/荷重/係数/反力/磁束/体積/境界成分改変、未完了・リンク・検査中変更・上書き拒否を確認した。

独立解析済み24例の48native/80CLIもPASS。標準1208件はout/validation-off-axis-magnetostatic-native-candidate-20260913へ終了0。固定候補は不変。新規依存・外部資料・旧版実行なし。S02/全計画は未完。

2026-09-13細分改訂：二層P1 n32の元H誤差2.398267e-2が2e-2を超えた。59例までの元候補/ログを保持し、この系列だけ8/16/64へ変更した別候補で全88例を再検証しPASS。製品・unit・解析参照・許容差は不変。標準検証は元候補の同一製品/unitの証拠として全hash差分を明示して継承する。

独立24例は235.476秒でPASS。
標準2436.300秒、1205合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは19.886秒でPASS。固定749sourceと主755source（不変egg-info 6件）は完全一致。独立例は候補hashに結び付け、主ツリーで同じ全例を再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。

標準検証のsourceは細分前の固定候補。製品・unit・解析参照・許容差は全件一致し、独立検証scriptの二層P1系列だけ8/16/32から8/16/64へ異なる。標準sourceと改訂sourceの全hash、および唯一の差分をseed_regression.jsonとp1-layer-H-refinement-decision.jsonで照合した。改訂候補で全標準を再実行したとは扱わない。
