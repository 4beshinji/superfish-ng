# 物理・数値仕様 — canonical specification v4（v1/v2/v3入力）

第4版では [真空m=0 TEの明示拡張](AXISYMMETRIC_TE.md) を追加する。以下の既存TMの式・規約は保持し、TEの未知数/PEC拘束・磁場phasor・加速量N/A・結果版を別契約にする。TEは直線P1/P2と[曲線P2](CURVED_TE_PLAN.md)に対応する。[通常Project/JobManager](TE_JOBS.md)も対応する。TE Study/追跡・調整・最適化・場の鏡映は未接続として拒否する。[通常GUI](GUI_TE.md)のTE選択・場表示・SIプローブ・N/A理由表示を接続した。

v3の明示物理モデルは [MODEL_CONTRACT.md](MODEL_CONTRACT.md)。本書の真空TM物理・
数式は変更せず、入力の版と物理モデルの版を区別する。

本ファイルの式はMaxwell方程式から今回の実装用に導出したものです。
公開の背景資料は [R1–R5, R11](REFERENCES.md)。旧SUPERFISHのアルゴリズムの転記ではありません。

曲線の細分優先度は[二次曲線残差指標](CURVED_RESIDUAL_INDICATOR.md)で、物理二階連鎖律と曲線流束から計算する。
指標は幾何近似誤差・周波数/RF/ピークの物理誤差上界ではない。

[RF重み付き選択](CURVED_RF_GOAL_INDICATOR.md)は固定二次領域の確認解における随伴残差優先度を追加する。
周波数項と場方向を合わせるが、物理誤差上界・通常の停止条件の代替ではない。

## 1. 対象と単位

円筒座標 `(r, φ, z)`、SI単位、真空、一様ε0・μ0、閉じた完全導体境界を仮定する。
profile系の断面領域は `0 < z < L, 0 < r < R(z)`。v1の`R(z)`は連続な正値折れ線。
v2のstepped_profileは正半径・z非減少の壁と孤立した垂直段差を許す。
arc_profileは半径・端点・回転方向が明示された短円弧を、最大弦誤差を指定した直線群へ近似する。
段差面も実在のPEC壁として弱形式と損失に含める。穴・内導体は扱わない。
v3 contourはz折返しを許す単一外周と連続した軸を表し、明示設定の自動メッシュまたは検証済み外部メッシュで計算する。
自己交差/接触を拒否し、局所端面タグを保持する（[一般輪郭](GENERAL_CONTOUR.md)）。
自動生成はmesh.contour_meshの全域最大辺長・最小角・要素/反復上限を使い、品質未達は拒否する。
幾何品質はRF精度を保証しない。契約と残件は[一般メッシュ](GENERAL_MESH.md)を参照。
v3 curved_contourはnative円/楕円/双曲線弧を保持し、弦近似または二次幾何写像で計算する。
二次曲線FEMはP2場に限定し、元の解析境界との差とFEM誤差を分離して検査する
（[曲線要素](CURVED_ELEMENTS.md)）。軸接続・単一真空・m=0 TMの範囲は変わらない。
`∂/∂φ=0`、磁場は `H = Hφ(r,z) eφ`、電場は `(Er,0,Ez)`。
一般形状では分離変数のTM0npというラベルは使わず、m=0 TMファミリーと呼ぶ。

phasorは `exp(+iωt)`、場はRMSではなくピーク振幅。
定数は `c=299792458 m/s`、`μ0=1.25663706127e-6 H/m`、`ε0=1/(μ0 c²)`。
μ0はSI再定義後は厳密定数ではなく、CODATA 2022中心値を固定している [R19]。

## 2. 強形式とPEC

Maxwell方程式から

\[
\nabla\times\mathbf H=i\omega\epsilon_0\mathbf E,\qquad
\nabla\times\mathbf E=-i\omega\mu_0\mathbf H.
\]

したがって

\[
-\partial_r^2 H_\phi-\frac1r\partial_r H_\phi
-\partial_z^2H_\phi+\frac{H_\phi}{r^2}=k^2H_\phi,
\quad k=\omega/c.
\]

真空側外向き法線を `(nr,nz)` とすると、PEC `n×E=0` は

\[
\partial_n H_\phi+\frac{n_r}{r}H_\phi=0
\]

である。円筒側壁に `∂r Hφ=0` を課す実装は誤り。
平坦な端板では `∂z Hφ=0`、円筒側壁では `∂r Hφ+Hφ/r=0`。
傾斜壁にも同じ法線条件を使う。軸は金属壁ではなく座標特異点。

## 3. 軸上正則化と弱形式

有限で正則な場は `Hφ=O(r)` なので、未知関数を `u=Hφ/r` とする。
離散空間で `u` は連続P1（既定）またはP2で、軸上でも有限。
v3のsolver.element_order=2がP2を選択する。両者とも同じ弱形式を使う
（[空間仕様](QUADRATIC_ELEMENTS.md)、[高次場・RF・保存](HIGH_ORDER_FIELDS.md)）。`Hφ=0` は自動的に満たされる。
滑らかな厳密解では `∂r u=0` だが、この導関数条件をP1節点へ追加しない。
軸上自由度も固有値問題に残す。軸上の `u=0` は誤った条件。

試験関数の磁場を `rv eφ` として、curl-curlのエネルギー形式を用いる。

\[
a(u,v)=\int_\Omega r\left[(2u+r u_r)(2v+r v_r)+r^2u_zv_z\right]drdz,
\]
\[
b(u,v)=\int_\Omega r^3uv\,drdz,
\qquad a(u,v)=k^2b(u,v).
\]

2πは両辺で消える。PECはこの形式の自然境界条件なのでDirichlet自由度を削除しない。
v2の平坦なz端対称面は別に指定する。`electric_symmetry` はPECと同じ自然条件
`∂z u=0` だが実在の金属面ではない。`magnetic_symmetry` は `Hφ=0`、すなわち
面上の `u=0` を本質条件として自由度消去する。軸との交点もこの端面条件を満たすが、
他の軸節点にu=0を課すことはない。どちらの対称面も壁損失と表面ピークの積分から除く。
確認用に部分積分すると、同じ剛性形式は

\[
a(u,v)=\int_\Omega r^3\nabla u\cdot\nabla v\,drdz
+\int_{\partial\Omega}2r^2n_r uv\,ds.
\]

境界項を捨てると別の問題になる。実装は展開前の非負エネルギー形をそのまま積分する。
P1が許されるのはこのスカラーTM縮約だからで、一般3Dベクトル電場に同じ節点要素を流用しない。
3D/m>0拡張ではH(curl)空間、勾配nullspace、軸上条件を別に設計する [R4,R5,R11]。

## 4. 離散化・固有値計算

以下の積分次数・多項式次数は既定の直線P1の仕様。直線P2は
[QUADRATIC_ELEMENTS.md](QUADRATIC_ELEMENTS.md)、二次幾何写像のP2は
[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md)に積分・場・保存契約を定める。
曲線写像の剛性被積分関数は一般に有理式となり、積分次数の収束を別に検査する。

- 要素は直線三角形。`u = Σ uj Nj`、面積座標Niは一次。
- 剛性被積分関数は3次、質量は5次の多項式。
- Duffy変換した4×4 Gauss積分を用いる。変換のJacobianを含め質量まで厳密積分可能。
- `K u = λ M u`、`λ=k²`。固有周波数は `c sqrt(λ)/(2π)`。
- `Dii=1/sqrt(Mii)` によって `(DKD)y = λ(DMD)y`、`u=Dy` と平衡化。
- `eigsh(..., M=B, sigma=0, which='LM')` で低い固有値を求める [R8]。
- 固定seedの開始ベクトル。縮退固有空間の基底が別環境でも同一になる保証はない。
- 残差は `||Ku−λMu||/(||Ku||+|λ| ||Mu||)`。1e-7超は失敗。
- 本質境界がある場合、残差は自由行だけで評価する。消去した行は境界反力であり、残差ではない。
- M内積の直交性と電気/磁気エネルギー差を記録する。

残差やエネルギー整合は離散方程式内の検査であり、メッシュ誤差やモデル誤差の保証ではない。
全モード検索は未実装。明示対応を用いる[部分空間追跡](MODE_TRACKING.md)と、
固定直線領域の[残差指標・適応細分](ADAPTIVE_REFINEMENT.md)を部分実装している。
残差指標や細分差は物理誤差上界ではなく、一般形状の精度/効率、曲線局所細分、表面量停止は未受入。

## 5. 電磁場復元

磁場固有ベクトルを実数に取ると

\[
H_\phi=ru,\quad
\widetilde E_r=-\frac{r u_z}{\omega\epsilon_0},\quad
\widetilde E_z=\frac{2u+r u_r}{\omega\epsilon_0},
\quad \mathbf E=-i\widetilde{\mathbf E}.
\]

出力の `quadrature` はこの実数の `Ẽ`。HとEが同時に最大になる意味ではない。
軸上は `Ẽz(0,z)=2u(0,z)/(ωε0)`。`H/r`を0/0で評価せず、極限を使用する。
uは連続、uの勾配は要素間で不連続。VTKのEはセル中心、軸CSVは軸上節点の線形補間。

## 6. エネルギーと壁損失

\[
U=\frac14\int_V(\epsilon_0|E|^2+\mu_0|H|^2)dV,
\qquad dV=2\pi r\,drdz.
\]

固有モードでは `UE=UH` なので `U=μ0π uᵀMu`。既定でU=1 Jに正規化する。
対称部分領域ではUも入力領域内のエネルギーであり、暗黙の全領域換算は行わない。
瞬時全エネルギーも理想定常固有モードでは一定で、この平均値に等しい。
損失計算では全PEC境界を回転した実表面を積分する。軸は表面損失に含めない。

\[
R_s=\sqrt{\frac{\omega\mu_0}{2\sigma}},\quad
P=\frac{R_s}{2}\int_S|H_t|^2dS,\quad dS=2\pi r\,ds,
\]
\[
Q_0=\frac{\omega U}{P},\qquad G=Q_0R_s.
\]

この形状ではHφはすべての壁に接する。端板の磁場損失も必要。
σは一様な常伝導金属の入力値。表皮効果の良導体近似と低損失摂動を仮定する。
損失による固有周波数シフトや空洞の温度を計算しているわけではない。

## 7. 加速量の規約

\[
V(\beta)=\int_a^b\widetilde E_z(0,z)
\exp\left(i\frac{\omega (z-z_0)}{\beta c}\right)dz,\qquad V_{acc}=|V|.
\]

全体の位相因子−iを除いて複素電圧を出力する。βc一定、ビームの摂動・速度変化は無視。
区分線形Ezと指数関数の積は解析積分し、低βでも積分点不足を起こさない。

\[
E_{acc}=V_{acc}/L_{acc},\quad
T_{abs}=V_{acc}/\int_a^b|\widetilde E_z|dz.
\]

`Tabs`は符号反転する多セル場でも0～1になる絶対値分母の規約。
`∫Ez dz`を分母に取る他のTTFと同一視しない。
既定は[a,b]=[0,L]、z0=0、Lacc=Lで従来結果を保つ。
v3 rfでvoltage_interval_m、phase_origin_m、active_length_mを別々に指定できる。
区間端は軸メッシュの節点に制限せず、端点補間で区分線形場を切って積分する。
U、Q0、G、壁損失、表面ピーク自体は入力領域全体の値を保つ。
仕様・鏡映時の写像・受入は [ACCELERATING_CONVENTIONS.md](ACCELERATING_CONVENTIONS.md)。

| 名称 | 定義 |
|---|---|
| `r_over_q_accelerator_ohm` | V²/(ωU) |
| `r_over_q_circuit_ohm` | V²/(2ωU) |
| `r_shunt_accelerator_ohm` | V²/P |
| `r_shunt_circuit_ohm` | V²/(2P) |

R/Qには分野や文献で係数2の違いがある [R2]。比較時には名称だけでなく式・phasor・Uを照合する。
EpkはPEC境界に接する要素の片側微分で計算した表面最大値。
直線P1のBpkは各境界上の二次式 `μ0 r u` の端点と停留点で最大化。
直線P2の場/RF評価は[高次場](HIGH_ORDER_FIELDS.md)、曲線P2の片側場・
連続離散極値の囲い込み・角診断は[曲線要素](CURVED_ELEMENTS.md)の版付き契約に従う。
直線P1/P2にも別API/保存/CLIで[連続離散ピークの囲い込み](AFFINE_SURFACE_EXTREMA.md)を追加した。
通常RFの推定値・保存規約は変更しない。離散場の極値を囲めても、連続物理場のピーク誤差や収束を保証するものではない。
Epk/Eaccは無次元、Bpk/Eaccは `mT/(MV/m)` で出力する。
Vが絶対値積分に対して1e-12以下なら、ピーク比はJSON nullとする。
折れ線角部の場が特異ならメッシュを細かくしてもEpkが有限値に収束しない可能性がある。

## 8. 独立解析ベンチマーク

半径R、長さLのpillbox、J0のn番目の正零点をχ0nとする。

\[
f_{0np}=\frac{c}{2\pi}\sqrt{(\chi_{0n}/R)^2+(p\pi/L)^2},
\quad n\ge1,\ p\ge0.
\]

TM010について `Ez=E0 J0(χ01 r/R)`、`Hφ=(E0/Z0) J1(χ01 r/R)`。

\[
T=|\operatorname{sinc}(\omega L/(2\beta c))|,
\quad U=\frac{\epsilon_0}{2}\pi R^2L E_0^2J_1(\chi_{01})^2,
\]
\[
G=\frac{\omega\mu_0RL}{2(R+L)},\quad
(R/Q)_{acc}=\frac{2LT^2}{\omega\epsilon_0\pi R^2J_1(\chi_{01})^2}.
\]

ここでsinc(x)=sin(x)/x。NumPy sincの引数はx/πにする。
Epk/Eacc=1/T。Bpk/Eaccは `max J1/(cT)`、最大J1は側壁ではなく端板上の途中の半径で現れる。
この解析モジュールはテスト専用で、FEMの値を置き換えたり較正したりしない。

## 9. 単一端面からの全空洞再構成

`reflect_solution` は一方の端が対称面、他方がPECの場合に限り、実際のメッシュと固有場を鏡映する。
電気対称ではu/Hφ/Ezは偶、Erは奇。磁気対称ではu/Hφ/Ezは奇、Erは偶。
共有面の節点は重複させず、反射要素の向きを修正し、対称面を内部面にする。
振幅は変えず、再構成後はUと壁損失Pが2倍、QとGは不変になる。
Vは反射後の符号付き軸場に通過位相を掛けて積分する。既定は全長、明示区間はR01の写像に従う。
半領域Vの単純2倍ではない。
再構成したK/Mで残差・直交性・エネルギーを確認するが、別の固有値計算や解析補正は行わない。
再構成出力のmode番号は選択した対称性の部分スペクトル内の順位であり、全スペクトルの順位ではない。
鏡映はprofile/stepped_profile/arc_profileに対応する。円弧半径・短円弧の向きを保持して
端点indexを反射し、面積とエネルギーの2倍関係を独立に検査する。
一般contourとcurved_contourにも対応する。曲線P2は固定二次写像と全係数を鏡映し、
元半領域から保存再構成する。詳細と左右/両対称の検証は[曲線要素](CURVED_ELEMENTS.md)。

## 10. 任意指定の交差分割

既定の四辺形の一方向対角線分割に加え、頂点平均の中心節点へ4分割する `crossed` を指定できる。
対称な格子ではz反射が三角形集合を保つ。周波数を合わせる補正ではなく、P1空間を増やす変更で、
弱形式・要素積分・場復元・RF積分は同じ。外壁の非一致高さ部分の三角形fanは変更しない。
7セル0/πモードの等振幅という独立不変量で検査するが、微小な加速電圧の精度保証とは分離する。
