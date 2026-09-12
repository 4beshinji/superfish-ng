# P03：閉じた真空同軸共振器のHφ固有場

後続の[Hφ表示/GUI](GUI_HPHI.md)を主ツリーへ接続・限定受入した。独立Study・収束・追跡は別工程。
専用[Hφ Project/Job](HPHI_JOBS.md)の入力・実worker・保存/取込・中止/再起動を後続工程で接続・限定受入した。GUIは[別計画](HPHI_GUI_PLAN.md)。
後続の[正半径の一般断面・複数穴](HPHI_MESH_RF.md)を専用形式で限定受入した。以下の円筒版1の入力・数値契約は保持する。

2026-09-12、基準3198adf。P03/K04/K11の最初の実装・検証工程。
FEM・場/RF・専用native/CLIまで主ツリーへ接続し、以下の範囲で限定受入した。

## 対象と先行不変量

内半径a、外半径b、長さL、`0<a<b` の真空同軸円筒を扱う。
内外の円筒面と両端の短絡板はすべてPEC。軸対称m=0で、磁場がHφだけを持つ場族が対象。
この場族にはTEMと半径方向に変化するTMが含まれる。周波数順位をTEM/TMラベルとは扱わない。
Eφを持つTE、有限方位角次数、材料、開端/ポート、任意内導体・曲線・複数の断面境界成分は未対応。

専用 `CoaxialCase` と専用native形式により、既存の軸接続Caseと平面Caseを暗黙に読み替えない。
既存Caseが内導体を拒否する状態から、次の独立不変量を先に定めた。

1. 静磁場 `Hφ=C/r` は真空内でcurlが0。係数 `q=rHφ` が定数のときKq=0でなければならない。
   この零モードをRF共振に含めたり、周波数で除算して電場を作ったりしない。
2. 両端短絡のTEMは `f_p=p c/(2L)`、p≥1で、正規化後のE/Hと両導体・両端板損失が解析式と一致する。
3. 半径方向に変化するTMのBessel境界条件を同じFEMが満たす。TEMだけを返す近似ソルバーにはしない。
4. 周波数・電場L2・磁場L2・壁別積分・G/Q/Pを別々に検証し、二尺度・実細分で確認する。
5. 保存readerは元メッシュ、静的零空間への直交、正の低位スペクトル、全場とRFを再検証する。
   改変後にhashを作り直しても、零モード混入・低位モード欠落・規約改変を拒否する。

TEMの短絡条件・正周波数とDC解の区別は[MIT公開講義15、pp.1–2](https://ocw.mit.edu/courses/6-013-electromagnetics-and-applications-spring-2009/002de9e0819bafcd2852219bcaa61b3e_MIT6_013S09_lec15.pdf)
を参照。FEM弱形式・SI/位相・同軸面の壁積分は以下で独立に導出した。

## 弱形式、零空間と位相

未知数は `q=r Hφ` [A]、座標は(r,z) [m]。PECでの自然境界条件は `∂n q=0`。
真空のMaxwellから

\[
 a(q,v)=\int_\Omega \frac{\nabla q\cdot\nabla v}{r}\,dr\,dz,
 \qquad m(q,v)=\int_\Omega \frac{qv}{r}\,dr\,dz,
 \qquad a(q,v)=\frac{\omega^2}{c^2}m(q,v)
\]

となる。`Hφ/r` を未知数とする軸正則TM空間とは異なる。
この断面はa≤r≤bの長方形であり、2D断面に独立した穴の境界成分を持つメッシュではない。
回転した3D真空領域は軸を含まず、静的な循環磁場が存在する。
Kの定数零空間をM内積で確認し、その一つだけを除いて正の低位固有値を返す。
残差や四則演算の小ささを空間離散化誤差の証明には使わない。

直線三角形P1/P2、共有中辺自由度、Duffy–Gauss積分を用いる。
1/rの積分は有限次数で厳密にはならないため、指定次数qとq+4のK/Mの相対Frobenius差を検査する。
差が5e-10を超えた場合は、半径方向細分または積分次数増加を要求して拒否する。
これは有限積分次数間の診断であり、真の誤差上界ではない。qは4〜32、三角形数は250000以下。
a=0は明示拒否し、微小なaを軸正則条件へ自動的に変換しない。

時間規約はpeak `exp(+iωt)`、この専用APIの場は **real + i*quadrature**。

\[
 H_{\phi,\mathrm{real}}=q/r,\quad
 E_{r,\mathrm{quadrature}}=q_z/(\omega\epsilon_0r),\quad
 E_{z,\mathrm{quadrature}}=-q_r/(\omega\epsilon_0r).
\]

その他のE/H成分は0。既存軸対称TMのẼ（E=-iẼ）と符号が逆になるため、
その出力を同じquadrature名だけで混合しない。nativeとプローブへ上記規約を保存する。

## 規格化・RF・解析比較

Uは全3D空洞の時間平均全エネルギー[J]、`dV=2πr dr dz`。
FEM係数は `U=μ0π qᵀMq` で規格化し、RF出力では場からUE/UHを高次積分し直す。
壁の接線磁場はHφで、内導体、外導体、z=0、z=Lの各実表面を別々に積分する。
各面の積分Iwallは[A²]、`dS=2πr ds`。

\[
 R_s=\sqrt{\omega\mu_0/(2\sigma)},\quad
 P=R_s\sum I_{wall}/2,\quad Q_0=\omega U/P,\quad G=Q_0 R_s.
\]

PEC固有場に対する低損失表皮効果の後処理であり、損失による固有周波数シフトは計算しない。
加速軸は内導体内なので、Vacc/Eaccと二つの明示名のR/Qは値Noneと理由を保存する。
有限の加速経路・ポート電圧は宣言していない。0というRF測定値にはしない。

TEMは `q=A cos(pπz/L)`。規格化は `A²=2U/(μ0π L log(b/a))`。
内外導体のIwallはそれぞれ `πA²L/a`、`πA²L/b`、各端板は `2πA²log(b/a)`。
端板損失を落とすとQ/Gが変わるので、側壁だけとの比較では受け入れない。

半径方向TMは `q=A R_n(r)cos(pπz/L)`、
`R_n=r[Y0(κa)J1(κr)-J0(κa)Y1(κr)]` とし、
`J0(κa)Y0(κb)-Y0(κa)J0(κb)=0` の正根κを用いる。
周波数は `c sqrt(κ²+(pπ/L)²)/(2π)`。Bessel方程式と導関数は
[NIST DLMF §10.2](https://dlmf.nist.gov/10.2)・[§10.6](https://dlmf.nist.gov/10.6)で確認し、
端面条件とこの組合せ・正規化・壁積分は独立に導出した。解析式は検証専用で、製品ソルバーはFEMを解く。

## API・CLIと保存

```python
from superfish_ng.coaxial import CoaxialCase, solve_coaxial
from superfish_ng.coaxial_saved import save_coaxial_run

case = CoaxialCase(.025, .05, .18, nr=16, nz=32, modes=4)
solution = solve_coaxial(case)
save_coaxial_run(case, solution, "new-coaxial-run")
```

```sh
python -m superfish_ng solve-coaxial examples/coaxial/shorted_coaxial.json --out new-coaxial-run
python -m superfish_ng replay-coaxial new-coaxial-run
python -m superfish_ng probe-coaxial new-coaxial-run --points examples/coaxial/probe_points.json --mode 1 --out new-coaxial-probe.json
```

nativeはcase/mesh/fields/resultsと最後に公開するmanifestで構成する。
元メッシュ・P1/P2自由度・正周波数・q係数を保存し、読込時に再組立・全量再計算を行う。
mode引数はAPIが0始まり、CLIが1始まりの周波数順位。追跡されたIDではない。
プローブは真空内のSI(r,z)点に元要素の場を評価し、E/H/B全real/quadrature成分と規約・元hashを新規JSONへ出す。
既存出力を置換しない。失敗した保存に完了manifestを作らない。
専用Project/Job、描画、GUI、Study・追跡への接続は本工程の後続。

## 検証手順と受入ゲート

```sh
OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_coaxial*.py' -v
OPENBLAS_NUM_THREADS=1 python scripts/validate_coaxial.py --out out/coaxial-new
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --out out/validation-coaxial-new
```

独立検証は二つの寸法比、二尺度、4低位モード、P1(64→128)とP2(24→48)の16FEM/native。
最終相対ゲートはP1がf 1e-3、E L2 3.5%、H L2 0.2%、各壁積分/G/Q/P 0.5%。
P2はf 1e-4、E L2 1%、H L2 0.1%、各壁積分/G/Q/P 0.5%。
いずれも実細分で各最大誤差が減少すること、U誤差1e-8、二尺度則1e-8を必須にする。
有限の保存場との比較であり、一般内導体形状の精度や表面ピークの保証ではない。

## 残るP03

任意の内導体・複数断面境界成分のメッシュ検査、一般形状の場空間と零空間の次元、
端条件の拡張、製品操作、旧版入力/実行の照合が残る。軸接続領域と軸非接続領域を
混ぜた一般トポロジーも未対応。この限定実装だけで親P03や全互換計画を完了にしない。

## 最終検証記録

主ツリー追加8unitは1.968秒で合格。二つの同梱例題を6つの実CLI操作で計算・全再読込・プローブ出力し、APIと照合した。
独立16FEM/native・64モード比較は66.247秒で合格。TEM p=1〜4とTM n=1,p=0/1を含む。
最終水準の最大相対誤差は次のとおり（両形状・両尺度・全4モード）。

| 量 | P1 | P2 |
|---|---:|---:|
| 周波数 | 4.016e-04 | 3.247e-06 |
| 電場L2 | 2.834e-02 | 2.550e-03 |
| 磁場L2 | 3.637e-04 | 1.028e-04 |
| G | 9.254e-05 | 5.241e-07 |
| Q0 | 1.427e-04 | 1.099e-06 |
| 全壁損失 | 5.292e-04 | 4.346e-06 |
| 個別壁積分 | 1.608e-03 | 1.293e-05 |
| 規格化U | 2.832e-12 | 2.787e-12 |

二尺度のf/G/Q/P/U則の最大差は9.082e-13。全ての指定誤差は細分で減少した。
独立条件を事後に緩めていない。最初の未実装テストはモジュール不在で起動失敗し、そのログを保持する。
最初の実装の3unit、保存/CLI接続後7unit、入力座標の型/位相検査追加後8unitは合格した。
初期の独立比較も16条件で合格。プローブのstrict入力検査を追加した最終固定版で再度16条件を実行した。

変更前の主ツリー全体979件（977合格・2skip、1595.088秒）、固定候補の全体987件（985合格・2skip、1626.390秒）が合格。
双方とも以前のResourceWarningなし。候補のconvergenceとseed9モード19量も合格し、既存ベンチマークは更新していない。
seedの周波数相対差0e+00、最大相対差8.882e-16。

全体検証は主ツリーの開始時回帰を変更しないため、同じインストール済みPython/NumPy/SciPyと明示PYTHONPATHを使った一時コピーで開始した。
候補・独立検証・全体検証・統合後の主ツリーは556 sourceが同一。主ツリーだけの6ファイルは既存editable installのegg-infoで、内容不変。
主ツリーでは追加8unitと全同梱例題を再実行した。通常の全987件を主ツリーで二度実行したとは主張しない。
実行時の版はPython 3.12.3、NumPy 2.5.2、SciPy 1.18.1、OPENBLAS_NUM_THREADS=1。hosted CIや旧版実行は行っていない。

証拠は `out/coaxial-development-20260912`、`out/coaxial-independent-frozen-20260912`、
`out/coaxial-main-examples-20260912`、`out/validation-coaxial-frozen-candidate-20260912`。
`seed_regression.json` が556共通source・主ツリー全562source・全独立native hash・旧数値比較の最終照合。
[複数断面境界の計画](COAXIAL_GENERAL_MESH_PLAN.md)は[一般断面Hφ FEM](HPHI_MESH_RF.md)へ接続した。Project/Job・[GUI](HPHI_GUI_PLAN.md)は後続。
