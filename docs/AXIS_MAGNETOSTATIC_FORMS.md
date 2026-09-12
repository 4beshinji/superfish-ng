# 軸に接続した磁静場の正則な材料・電流・弱形式

2026-09-13 JST。[計画](AXIS_MAGNETOSTATIC_FORMS_PLAN.md)の固定723sourceを主729sourceへ統合し、正則弱形式API範囲で限定受入。
候補は `/tmp/superfish-axis-magnetostatic-forms-20260913`。

`AxisMagneticPartition`は直線AxisConnectedMesh、正値実数mu_r、全領域/セル所有、界面・面積・回転体積・reluctivityを保持する。明示穴0/1/2を検証した。幾何JSONは軸接続の外周・穴・点・三角形だけで、既存RFメッシュのPEC宣言を持ち込まない。内部では幾何・所有・SI測度の検証だけを既存RF材料から共有し、RF演算子や境界条件は使わない。

`axis_magnetostatic_forms`は正則な未知数a=Aphi/r[T]を用い、Br=−r∂z a、Bz=2a+r∂r aから磁気エネルギーを組み立てる。K=∫ν B_i·B_j dV [m⁴/H]、f=∫Jphi r Ni dV [A m²]、dV=2πr drdz。Jphiは各領域で一定の符号付きA/m²を明示する。源電流∫Jphi drdz[A]と、荷重和2π∫Jphi r²drdz[A m²]を区別する。

軸のa自由度を保持し、Aphi=r*aにより軸上Aphi=0と有限なBを構成する。定数aはBz=2aの一様磁場であり、平面Azの定数gauge核とは異なる。先に、平面のgrad形式をそのまま用いるとこの磁場のエネルギーがゼロになる矛盾を特定した。軸非接続領域のAphi=C/r gaugeは別仕様が必要なため拒否する。aの境界値を暗黙にゼロへ拘束しない。

追加5unitがPASS。独立72例は穴0/1/2、P1/P2、材料3パターン、尺度0.5/2、z移動0/−0.25m。独立18×18 Gauss/VandermondeのK/f、72正値スペクトル、216解析多項式の磁気エネルギー/源仕事、72一様Bエネルギー、mu逆比例・電流反転・領域順序・JSON往復を照合する。一定a係数でK∝s³、f∝s⁴、mu倍率でK逆比例を検査した。積分される磁気エネルギーはJであり、平面のJ/mとは異なる。

独立記録は `out/axis-magnetostatic-forms-independent-20260913/report.json`、5.294秒でPASS。最大相対差はK 2.462e-15、f 2.127e-15、尺度/z移動5.576e-16、多項式6.551e-15、電流/源仕事和6.662e-16、mu逆比例3.015e-16、一様Bエネルギー6.551e-15。最小/最大固有値比の全例最小値は3.171e-6で正。新規5unitは0.793秒でPASS。

標準1181件は `out/validation-axis-magnetostatic-forms-candidate-20260913` へ終了0。固定候補は不変。
境界付き磁静解、元場/磁束の出力、軸非接続、曲線、非線形/異方性/永久磁石、保存/CLI、外部境界診断は後続工程。新規依存・外部資料・旧版実行なし。S02と全計画は未完。

標準2311.079秒、1178合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主5unitは0.806秒、主独立72例は5.346秒でPASS。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
