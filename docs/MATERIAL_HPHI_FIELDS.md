# 材料重み付き元E/H内積

2026-09-22。H15-bの元場比較を実装・検査済み。scalar質量射影はまだ未実装であり、H15-b/親H15を完了扱いしない。[固定材料契約](MATERIAL_HPHI_TRACKING.md)と[全領域/界面比較](MATERIAL_HPHI_COMPARISON.md)に従う。

`material_hphi_field_grams(previous, current, comparison, ...)`は専用`MaterialHphiSolution`二つと完全な`MaterialHphiComparison`を受け取る。前後のpartitionは元nativeの宣言と完全一致が必要。元の材料K/M、係数、正の低順位スペクトル、全空間/界面配列を再検証してから、元セル指定で片側E/Hを評価する。元場を真空Caseへ付け替えず、材料平均や界面平均を行わない。

返り値は`MaterialHphiFieldGrams`。electricとmagneticの各tupleは前自己/cross/現在自己の順。単位は両者ともJで、既存の無重み真空Gramの単位とは異なる。peak phasorで自己対角は総蓄積エネルギーの2倍。Eの内積はepsilon0 epsilon_r、Hはmu0 mu_rと全3D体積2πr dr dzで重み付けする。Bを無重みHの代用品にしない。

crossは前後の元材料・体積密度の平方根積を使用する。固定円筒成分のエネルギーL2単位的比較であり、Maxwell方程式の座標変換・周波数補正・連続問題の誤差上界・ID追跡ではない。

自己Gramは別に元行列から、Eを`2π/epsilon0 CᵀKC/(omega_i omega_j)`、Hを`2π mu0 CᵀMC`として再計算し、両側の元エネルギーを再現することを検査する。二つの積分次数間の正規化差は既存場比較と同じ1e-10、元Gram差は1e-8、joint Gramの半正定性も検査。係数の共通符号を保持し、元のf/規格化/RFを変更しない。

比較領域/全界面の予算に加え、`max_gram_modes`と`max_sample_points`（各側・各積分次数の点数）を明示検査する。標準積分次数は両元Caseの次数+4と16の最大、その+4でも検査する。明示次数は4〜36。格納は65,536 sample×modeを目安に三角形単位で分割し、点・モードを省略しない。入力不正/予算超過/未解決求積はValueErrorで、部分的成功を返さない。

## 検査と来歴

`out/h15-material-fields-20260922/`。最初のredは専用API未実装。初期3件は7.471秒PASS。その後の`expanded.log`は新5件＋関連8件、25.023秒PASS/終了0、全handle終端。

新`test_material_hphi_field_overlap`では次を確認した。

- 製品の場評価・三角求積を使わず、別のtensor Gauss積分と局所Vandermonde多項式再構成で、区分材料のE/H自己Gramを検査。P1/P2、正半径/穴付き軸、元RF全量と係数の不変を確認。
- 固定材料の全空間2倍尺度でf/2、元自己Gram保持、cross対角の絶対値2U、共通係数位相、正逆cross転置を検査。
- 非一様写像の独立製造積分で、領域ごとの体積比8/4と材料密度の平方根積を検査。これは積分核の試験用integrandでありFEM共振器の代用品ではなく、公開APIはそのオブジェクトを拒否する。
- 真空係数1の専用材料Caseを独立にsolveし、真空比較のE Gram×epsilon0/H Gram×mu0と照合。一様epsilon_r=4/mu_r=9のf/6と重み付きエネルギーも検査。
- 元partition不一致、空間改変、モード/求積点予算不足を拒否。モード予算は復元計算前に拒否する。

関連は`test_material_hphi_comparison`7件と、`test_material_hphi.MaterialHphiTests.test_uniform_material_frequency_fields_energy_and_metal_wall_scaling`。後者は独立のE/2・H/3・B×3と壁金属/RF規約を保持する。

既存の自作材料弱形式・元片側場評価・正確な界面overlayを再利用し、物理重みの自己/cross Gramを追加した。新規外部資料・依存・legacy参照なし。FEM組立/固有解/元RF/seed TMを変更していないため、当該独立積分と直接利用先に限定して検査した。全suite・有限比較スペクトル・ID追跡の受入を主張しない。次はmu_r重み付きq/u質量射影。
