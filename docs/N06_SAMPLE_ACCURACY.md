# N06：元場と量別参照の有限標本判定

2026-10-08 JST：temp commit611f548の新module/testを主へ同byteで統合した。
元1417対象源は不変、新1419対象/1212 Python源。新8個別unitの元証拠を再利用し、
統合のためのunit/FEM/seed/full/12benchmark再実行は0。
rawは `accuracy-leaf-acceptance.json` と `accuracy-leaf-main-integration.json`。
以下の主統合待ちは限定受入時点の履歴である。

2026-10-08 JST、N06参照比較の数学leafだけを限定受入する。
先行は[N05の共通精度](N05_ADAPTIVE_EFFICIENCY_PLAN.md)と
[元Case/sourceを固定した実行計画](N06_FIXED_EXECUTION_PLAN.md)。N06はIN_PROGRESS。

`adaptive_efficiency_accuracy.assess_efficiency_samples` は全標本のEr/Ez/Hφ、
全体積重み、物理軸Ez/軸重み、元RFと離散peak比の両端を受け取る。
N03と同じnativeの元L2 normを分母にし、Hφから一つの符号を選んでE/H/軸へ共通適用する。
振幅fit・領域縮小・欠測点の削除をしない。
計算の共通尺度でoverflowを避けるが、場の相対振幅・元分母を変えない。
正の重みでも共通尺度への変換で0となる場合はUNVERIFIEDにし、点を無言で捨てない。

f1e-4、両R/Q・G0.005、peak比0.01、E/H全域0.005、物理軸Ez0.01を別gateにする。
両R/Qのfactor2を元/参照の両側で確認する。
peakは上下界両端の最悪差を評価し、推定値1点の一致で代用しない。
有効な広い区間の下端0は誤差として評価し、欠測と呼ばない。
反対のE符号をHとは独立に反転して合格へ救済しない。
欠測/非有限/不正shape・ゼロH/軸norm・不正規約では全誤差をnull、全gateをfalseにする。
周波数PASSを場/RF/peakのPASSへ昇格しない。

PASSは与えた有限標本の量別判定だけ。
physical_acceptance_status=SOURCE_DOMAIN_REFERENCE_CHECKS_REQUIREDを常に保持し、
完全Case/元P2領域/全点被覆/実個別ID/独立参照byteと両側二区間は外側で検証する。
物理誤差上界はnullで、一般PDE精度・厳密な連続最大値を証明しない。
このleafを実参照格子とnative保存場へ接続する工程は後続。

## 独立数学不変量と証拠

未実装moduleのImportErrorをbaselineとして保全した。
初稿7件0.002秒は6件PASS、有限peak区間[0,2]をUNVERIFIEDとする反例1件FAIL。
区間の下端は非負が正しく、[0,2]/参照1の最悪誤差は1でFAILである。
下端validatorを訂正し、重みの尺度変換で標本が失われる反例も追加した。
共有norm/peak入口を変更したため新8個別unitを一度実行し、0.001秒・終了0/PASS。
反復分を別の個別件数へ数えず、元FAILと費用を保存する。

独立の手計算により、元場を1.006倍した差が0.006/1.006となり、
freq一致でもE/Hは0.005未達でFAILとなることを確認した。
単一の負符号で全場が一致する例、Eだけ逆符号で相対差2となる例、
推定値が一致してもpeak上端1.02でFAILとなる例を確認した。
入力arrayのbyte値不変、返したlimitsの外部変更が元閾値に漏れないこと、
非有限/欠測/ゼロnorm/ゼロ重み/complex型/RQ規約不一致と相対重みunderflowの
UNVERIFIED/nullを確認した。これは合成arrayの数学検査であり、独立Maxwell実測ではない。

tempの明示PYTHONPATH/主uv環境で
`python -m unittest -v test_adaptive_efficiency_accuracy` を実行した。
元1210 Python源はmainと不変、新二源込みtemp1212 Python/全1413点
（主の生成egg-info六点なし）を確認する。mainの元1417対象源は不変。
新FEM/seed/full/legacy/12benchmarkは0。
rawは `out/n06-cost-recording-20261007/accuracy-leaf-*.log` と
`accuracy-leaf-acceptance.json`。主同byte統合と実参照/worker接続は後続。
この限定受入でN06・親N04・全goalを閉じない。
