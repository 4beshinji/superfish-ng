# 材料scalar質量結合と射影

2026-09-22。H15-bの[元E/H比較](MATERIAL_HPHI_FIELDS.md)に加え、固定材料q/uの質量結合・射影を受入。材料有限スペクトルとID追跡はH15-cに残る。

`material_hphi_mass_coupling(comparison, ...)`は完全な`MaterialHphiComparison`とP1/P2次数を受け取り、両側を専用`material_hphi_matrices`で組み立てる。全領域/界面の対応を検証し、元のmu_r質量行列とcross行列を返す。静的定数q、軸上自由度を含む全scalar空間を保持する。

qの測度は`mu_r dr dz/r`、uは`mu_r r^3 dr dz`。共通三角形の各側で元材料値、半径、Jacobianを使い、crossを両密度の平方根積で積分する。`2π mu0 CᵀMC`は元Hの磁気エネルギーGram（固有場の自己対角2U）。固定円筒成分の単位的比較で、Maxwell変換ではない。異方的幾何尺度r→sr*r、z→sz*zではq係数の移送率sz^(-1/2)、uはsr^(-2) sz^(-1/2)。材料係数自体を変える比較は拒否する。

`project_material_hphi_coefficients(comparison, coefficients, ...)`は`M_current x = Cᵀ coefficients`を解く。元質量ノルム、射影後ノルム、直接積分した差、相対損失、線形残差、Pythagoras欠損を返す。差は密度平方根で重み付けした両場から計算し、ノルム差の桁落ちに依存しない。ゼロ列を保持し、非ゼロ列の質量underflowは再尺度を求めて拒否する。係数は読み取り専用で、周波数・RF・新たな固有モードを付与しない。

求積差1e-10、元質量再現1e-8、射影残差1e-10、Pythagoras欠損1e-8を検査する。正半径/写像ありの積分次数は指定次数+4/+8、同領域uは5/7。直接差は高次数とその+2。領域/界面予算に加え、自由度、各次数の積分点数、係数列数の明示上限を検査し、点や列を省略しない。元のFEM解・規格化・RF計算は変更しない。

## 検査と来歴

`out/h15-material-projection-20260922/`。`before.log`で未実装APIのredを確認。`initial.log`の新4件12.336秒PASS、`independent-related.log`の追加1件＋元場比較5件17.041秒PASS、`nonuniform.log`の追加1件PASS。新6件は分割実行証拠であり、全suiteではない。全handle終了0。

- P1/P2、正半径/穴付き軸、独立細分で多項式再現、解析的材料別定数質量、軸自由度と定数qを検査。
- 別tensor Gaussと局所Vandermondeで全質量行列を独立積分し、実材料固有場の磁気エネルギーとも照合。
- P2→P1粗視化の正の損失、直交条件、Pythagoras、ゼロ列、入力不正/予算/underflow拒否を検査。
- 異方的尺度の係数則、正逆cross転置、非一様写像の材料別質量比（qで2/1、uで32/16）、真空係数1の専用材料経路と既存真空結合の一致を検査。

既存自作scalar基底・疎行列射影の構造を使用し、材料元行列と両側密度による積分を追加した。新規外部資料・依存・legacy参照なし。材料弱形式や固有値solver、seed TMを変更していないため、独立積分と直接利用先に検査を限定した。
