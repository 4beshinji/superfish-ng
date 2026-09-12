# 軸対称静電の専用保存・再構築・CLI

2026-09-13 JST。[計画](ELECTROSTATIC_NATIVE_PLAN.md)に従う固定候補687sourceを主693sourceへ統合し、専用保存/CLI範囲で限定受入。
候補は `/tmp/superfish-electrostatic-native-20260913`。主ツリーにも反映・再検証済み。

`save_electrostatic_run` はCase、材料/界面・全境界条件・DOF・全体積/境界荷重、
基準電位、基準からの電位係数、絶対電位、全静電量を保存する。
5ファイルはcase.json、mesh.npz、fields.npz、results.json、manifest.json。
原本のスナップショットを取り、検証した一時ファイルを公開し、manifestを最後に作る。
既存ディレクトリ・リンク・不完全な公開を受理しない。

`restore_electrostatic` と `read_electrostatic_run` は同じ明示材料/電荷/境界のPoisson問題を再構築・再求解し、
保存された電位係数がその一意な固定電極問題に適合するかを検証する。
固定電位、基準値、絶対電位の関係、自由DOF残差、全配列の型と内容、静電量と規約を再検査する。
元係数からの再生値を使うため、場・反力電荷・元Dの表面電荷・容量の定義を保持する。
係数は相対1e-10のPoisson解/自由DOF残差と、固定電位の一致で検証する。

専用CLIは `solve-electrostatic CASE --out NEW`、`replay-electrostatic RUN`、
`probe-electrostatic RUN --points POINTS_JSON --out NEW_JSON`。
座標は[r_m,z_m]。静電プローブにmode・phasorを持ち込まず、Phi/Er/Ez/Dr/Dzと片側の材料情報を出す。
`capabilities.axisymmetric_electrostatic` に形式・単位・境界・容量の条件を明記する。
RFのcanonical Modelと既存Hφ形式は変更しない。Project/GUI/Studyは未対応と明記する。

追加4unitは5.957秒、既存能力表3unitは5.969秒でPASS。
13種類のhash再作成後の不整合、リンク、読み込み途中の変更、公開中断を検査した。
`out/electrostatic-native-cli-smoke-20260913` の3 CLIはPASSで、API/CLIの保存5ファイルがbyte一致し、プローブJSONも一致した。
独立物理検証のPASS後、その二層8・製造解12・同軸4の計24例を48 native保存・79 CLIで照合し、候補・本体ともPASS。元240 nativeと参照106ファイルは不変。

標準1142件は `out/validation-electrostatic-native-candidate-20260913` へ終了0。
新規依存・外部資料・旧版実行なし。平面・Project/GUI/Studyなど、S01と全計画は未完。

標準2255.990秒、1139合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは5.930秒、主24例79CLIは99.195秒。候補687sourceと不変egg-info 6件を加えた主693sourceを照合。既存しきい値・ベンチマークは不変。統合証拠は標準出力内seed_regression.json。
