# 平面曲線P2の幾何・弱形式・受入契約 — P05

2026-10-02、基準 `0937087`。本書はP06〜P09の実装仕様であり、曲線平面solverの受入証拠ではない。
現行の平面製品入力は矩形版1と直線多角形版2。以下の版3・API・検査名は新設する契約。
[原P05](development-plan/03-planar.md#p05)の条件と[既存平面RF契約](PLANAR_RF_PLAN.md)を維持する。

## 物理範囲と共有境界

真空、単一連結のdisk位相、閉じた単一PEC外周、Cartesian xy断面、z方向一様、βz=0。
TE/TMはz方向に対する偏波。任意の有限xy座標を許し、負のxやy=0に軸条件を付けない。
一般材料、βz≠0、穴/TEM、開放境界、対称面、有限長端板はstrict拒否する。
円/楕円は数学的な合成検査形状であり、測定構造ではない。

`planar_curved.py`で専用Domain/Case/Space、`planar_curved_fem.py`で面積K/Mを新設する。
局所P2基底・参照Gauss則・座標に依存しない多項式計算を既存自作数学から再利用できる。
`curved_fem.mapped_element_matrices`、Hφ/TEの軸対称組立、Case/軸タグ、r正値条件は呼ばない。
x/yをr/zへ改名して既存の物理空間へ渡す経路は作らない。Cartesianの場評価/壁積分も専用経路とする。
既存平面版1/2とcanonical TMの行列・保存規約を変更しない。

## 二次領域と全域検査

参照三角形はξ≥0、η≥0、ξ+η≤1。λ=(1−ξ−η,ξ,η)。
節点順は頂点0/1/2、その後に辺01/12/20の**参照**中点3/4/5。
中点の物理座標を端点平均に置換しない。

```text
N_i = λ_i(2λ_i−1)                       (i=0,1,2)
N_3 = 4λ_0λ_1, N_4 = 4λ_1λ_2, N_5 = 4λ_2λ_0
F(ξ,η) = Σ_i N_i X_i,  X_i = (x_i,y_i) [m]
J[a,b] = ∂F_a/∂ξ_b,  dA = det(J) dξ dη
∇_xy N_i = J^(−T) ∇_ref N_i
```

入力Domainは全節点xy、六節点cell、向き付き外周三節点edgeを保持する。整数番号、有限実数、
重複/未使用節点、重複cell、共有mid不一致、非conforming辺、未知項目/版/型を拒否する。
boolを座標や番号として受け付けない。各edgeのmidは一意で、vertexと同じ番号にはできない。
共有edgeは端点向きが逆でmidが同じ。外周edgeはcell incidenceから得た全一側辺に完全一致し、
同じmidを含む一周のCCW列を宣言する。外周の閉じる頂点を追加重複して保存しない。

各cellのdet(J)は参照座標の二次多項式。binary64入力を正確な有理数へ持ち上げて係数を求め、
頂点/各辺の停留点/内部停留点で閉三角形全体の最小を調べる。正のBernstein下限を先に使ってよい。
頂点や求積点だけで正値を確認しない。符号不正、零点、浮動小数演算の局所分解能不足はFEM前に拒否。
正の厳密最小だけで逆行列の数値信頼性を主張せず、局所尺度/係数に対する丸め余裕も記録する。

全cellのedge隣接連結性、V−E+F=1、単一の次数2外周を確認する。
全unique二次edgeの曲線接触/交差、共通端点以外での重なり、T接続を検査する。
Bezier制御点の囲い/保守的box候補と分割で判定し、有限予算で判定できない入力はUNVERIFIEDとして拒否する。
単に全局所Jacobianや総面積が正しいことを全域被覆の証拠にしない。
独立Green境界面積 `1/2∮(x dy−y dx)` とcell面積和の一致も別に確認する。
境界tangentは二次edgeの実微分、ds=|γ′(t)|dt、外向きn=(t_y,−t_x)を使う。
頂点の弦tangent/弦長を曲線壁へ代用しない。境界評価は所有cellの片側場。

幾何検査予算 `max_geometry_boxes` は全候補/再分割で消費したbox検査の総上限。
予算超過で近似的にPASSにせず、使った件数/上限と不確定なedge pairを保存する。

## 面積FEM・零空間・数値積分

両偏波で `Kq=k²Mq`、ω=c0k、f=ω/(2π)。未知scalarはTEの実Hz、TMの実Ez。

```text
K_ij = ∫_Ω ∇N_i·∇N_j dA
M_ij = ∫_Ω N_i N_j dA
TE: ∂n Hz=0 (全PEC外周で自然境界)、全節点が自由
TM: Ez=0 (全PEC外周の頂点/mid節点が本質拘束)
```

TEの定数vectorを唯一の静的核として検査し、正のlowest spectrumだけを返す。
任意節点固定、定数へのpenalty、解析周波数への差替えは使わない。
負shiftは断面の有限幅から尺度を定め、Neumann零点を確認してから除外する。
全正モードの質量直交/定数直交、TM拘束と正値、lowest positive spectrumを再検証する。
モード数が自由度を超える場合は細分/要求数の修正を促し、モードを複製しない。

Mの被積分は参照次数6。Duffy product Gaussのorder≥4で多項式Mを積分できる。
KはJの逆を含む有理関数、曲線壁積分はさらにdsの平方根を含む非多項式なので、固定次数で厳密とはしない。
Caseにarea orderとwall orderを保存する。既定候補は8/12、受入では8/12/16等の増次数を別に確認し、
最後の二次数でfと全RFの相対差≤1e−8、行列/独立積分は対応する誤差規準を満たすこと。
次数を変更した計算はそのCase/metadataと結果を新出力へ保存し、保存readerで同じ次数を再組立する。

代数ゲートは既存平面と同じ残差≤1e−7、質量直交誤差≤1e−8、TE定数混入≤1e−8、
零固有値の無次元差≤1e−8。いずれも幾何/FEM/壁誤差の判定とは独立。

## 元場・規格化・PEC壁RF

時間phasorはpeak exp(+iωt)。quadrature値を+ i倍したものが複素場。

| 偏波 | real | quadrature | 残りの成分 |
| --- | --- | --- | --- |
| TM | Ez=q | Hx=∂yq/(ωμ0), Hy=−∂xq/(ωμ0) | 0 |
| TE | Hz=q | Ex=−∂yq/(ωε0), Ey=∂xq/(ωε0) | 0 |

六つのCartesian成分のreal/quadrature、計12成分を明示し、曲線幾何の元P2係数から実点で評価する。
同じ元cell/ref点のqとJ^(−T)勾配を使う。描画用の直線再三角形や解析場を評価に使わない。
点検索は曲線の制御点boundsと検証した逆写像を用い、閉参照三角形の所属/逆写像残差を確認する。
共通境界は最小cell番号を片側所有者にする。外点を許容差で領域内へ広げず、境界近傍の
所属が不確定な場合はactionable errorとする。直接cell/ref APIは閉三角形だけを受け付ける。

```text
U′e = ε0/4 ∫|E|² dA, U′m = μ0/4 ∫|H|² dA, U′=U′e+U′m [J/m]
W_H = ∮|H_tan|² ds
P′ = Rs W_H/2 [W/m], Rs = sqrt(π f μ0/σ)
Q0 = ω U′/P′, G = Q0 Rs = 2ωU′/W_H [Ω]
```

TEのH_tan=Hz、TMは横Hと二次edgeの単位tangentとの内積。
scalar mass normは `∫q²=2U′/μ0` (TE)、`2U′/ε0` (TM)。派生場のエネルギーも独立積分して等分配を確認する。
標準規格化はU′=1 J/m、σ=5.8e7 S/m。別の正の規格化/導電率も明示値として保持する。
Vacc/Eacc/RQ_accelerator/RQ_circuitはnullとし、有限加速経路のない遮断断面という理由を保存する。
有限長端板/3D空洞損失や伝搬電力を加えない。

一様尺度sでf→f/s、固定U′で全非零E/H→E/H/s、G不変、同じσでQ0→√s Q0。
回転/平行移動の対照ではCartesian vectorを同じ回転で変換し、scalar/面積/RFを維持する。
単一符号、または完全縮退群の単一直交変換をscalarから決め、E/Hに同じ変換を適用する。
EとHの独立した位相/基底合わせ、縮退内の順位を永続IDにすることは認めない。

## 円形の独立解析対照

半径aの真円でq=A J_n(αr/a)cos(nθ)。n>0はsin(nθ)も含めた二次元の完全縮退群、n=0は一モード。
αはTMならJ_nの正根、TEならJ′_nの**正根だけ**。f=c0α/(2πa)。
本書のsは正根の序数なので、J′_0の零点0を数えるDLMFの添字とは区別する。
これらの零点/導関数は[NIST DLMF §10.21](https://dlmf.nist.gov/10.21)、
[§10.6](https://dlmf.nist.gov/10.6)を独立参照にする。

角積分C_n=2π (n=0)、π (n>0)と置き、scalar単位振幅の面積積分を

```text
I = C_n a²/2 [J′_n(α)² + (1−n²/α²)J_n(α)²]
A_TE = sqrt(2U′/(μ0 I)), A_TM = sqrt(2U′/(ε0 I))
G_TM = Z0 α/2
G_TE = Z0 α/2 (1−n²/α²), Z0=μ0 c0
```

とする。Iは[DLMF 10.22.5](https://dlmf.nist.gov/10.22.E5)と漸化式から得られる。
Gは本PJのU′/実側壁H積分から独立導出した式で、有限長円筒共振器のGを流用しない。
原点のJn/勾配は[DLMF §10.7](https://dlmf.nist.gov/10.7)の極限を使い、n/rを直接0で割らない。
全scalar/派生場、面積/壁積分と符号付きMaxwell curlを独立に照合する。
公開講義[Waveguides](https://farside.ph.utexas.edu/teaching/jk1/Electromagnetism/node117.html)の
cutoff/伝搬の区別を参照したが、本書の+時間phasorとβz=0の場/RFは自分で導出した。

円形受入はa=0.01/0.02 m、TEの7正モード、TMの6正モード、両偏波。
TE対象はTE11二重/TE21二重/TE01単一の先頭5、guardはTE31二重。
TM対象はTM01単一/TM11二重の先頭3、guardはTM21二重、追加TM02単一まで保存する。
分裂した数値基底も完全解析群で比較し、guard不足や群の切断はUNVERIFIED。

## 幾何近似と固定P2領域のFEM細分

円/楕円の境界の端点・角度中点を解析形状で生成し、それらを通る二次edgeを明示保存する。
このP2辺は真円/真楕円の厳密な弧ではない。解析形状宣言を元nativeの代用にしない。
初期メッシュは4同心ring、角分割N≥16、中心fan/隣接ringの三角形、境界midは角度中点。
内部midは端点平均。全Jacobian/外周を検証し、不正なら生成器を修正して新入力を作る。

| 系列 | 入力と独立する変更 | 判定 |
| --- | --- | --- |
| 固定二次領域 | 一つの初期P2 Domainを参照4分割でL=0/1/2へ制限 | 元P2写像/外周と面積を維持し、f/E/H/RFのFEM差だけを比較 |
| 幾何近似 | N=16/32/64で解析円/楕円から別の初期P2 Domainを生成 | 真形状への境界距離・面積/周長誤差と、各Domainの十分細かいFEMを別に記録 |
| 独立内部mesh | 同じ初期chartを頂点→対辺midの二分割から細分するB系列 | 四分割A系列と同じ初期二次領域を比較し、元場を共通参照上で別々に評価 |

粗い水準が物理gate未達ならLやNを追加し、既定許容値を変えない。
子の六節点は親Fと参照座標から生成し、円/楕円へ再投影しない。
binary64で親写像の制限係数に差が生じる場合、参照対応・親全被覆・差の外向き上限と
局所分解能を記録する。不確定な差を「同一領域」として黙って扱わない。
P09の同領域比較/最終調整でもこの契約と元nativeを保持する。

## 検査入力と固定した個別gate

以下はP06/P07専用validatorへ実装する条件であり、P05でFEMがPASSしたという表ではない。

| 入力 | 独立基準 | 合格gate |
| --- | --- | --- |
| 曲線一要素patch F=ℓ(ξ,η+dξ(1−ξ−η)), d=1/5、ℓ=0.01/0.02 m | 面積ℓ²(1/2−d/6)、x一次moment ℓ³(1/6−d/12)、y一次moment ℓ³(1/6−d²/60)、Green境界積分 | 面積/規格化moment相対差≤1e−12。q=x/y/定数のP2再現とK勾配Gram相対差≤1e−12 |
| F=((ξ−1/4)²−(η−1/4)²,2(ξ−1/4)(η−1/4)) | detJ=4[(ξ−1/4)²+(η−1/4)²]、内部零点 | 全域Jacobianで拒否。正の頂点/求積サンプルを合格根拠にしない |
| 直線P2矩形と凹L字のmid=端点平均 | 既存のCartesian版1/2 K/M、面積/周長、線形patch | 対応するDOFの行列相対norm差≤1e−12。TE核1個/TM拘束後正値。xy負座標への平行移動でも成立 |
| 円、両半径/偏波/対象完全群、三水準 | 上のBessel f/全E/H/G、独立面積/壁積分 | 最終f相対誤差≤1e−4、E/H各群L2相対誤差≤1%、G相対誤差≤0.5%。一つでも未達なら未受入 |
| 固定円P2 DomainのA/B内部mesh | 共通親chart上の元全E/H、各元RF | 最終二水準/独立A対Bのf差≤1e−4、E/H各差≤1%、P′/G/Q各差≤0.5%。解析誤差とは別判定 |
| 滑らかな楕円a=0.02,b=0.012 m、その2倍、中心(−0.03,0.01) m、回転π/7 | 真面積πab、真周長4a E(1−b²/a²)の独立1D積分、固定P2 DomainのA/B系列 | 幾何系列の最終面積誤差≤1e−4/周長≤1e−4、固定FEM差はf≤1e−4/E,H≤1%/RF≤0.5%。真形状への距離≤1e−4 a。楕円fを円の一変数倍率で置換しない |
| 特異角L字、a=0.01/0.02 m、外周(−a,−a),(a,−a),(a,0),(0,0),(0,a),(−a,a) | 面積3a²/周長8a、3π/2再入角。局所調和q~r^(2/3)sin/cos(2θ/3)から∇q~r^(−1/3)、壁二乗積分は可積分 | 角近傍を細分し、固定FEMのf/E/H/積分RF差を同じgateで確認。角の有限peak/解析絶対f/Gは主張しない |
| 一様尺度2、平行移動/回転 | f/全E,H/G/Qの上述尺度則とvector変換 | f/G/Q相対差≤1e−8、E/H相対L2差≤1e−8。元場の同符号/同群変換を使用 |
| 増求積次数、strict/改変/予算不足 | 別Gauss/Green積分、元境界全被覆、完全native再生 | 前節の積分/代数gate、不正入力のFEM前拒否/改変拒否。曲線を直線fallbackにしない |

L2は完全領域の実面積で積分する。円解析場は実Ωh上に評価し、真円との差は幾何gateに別保存する。
同じ群変換によるscalar整合を確認し、E/Hを別に比較する。表面の点peak検査をL2/RFの代用にしない。
再入角のr^(2/3)場は角/積分器の独立局所対照であり、全L字の固有場として返さない。
非円形の有限差/独立mesh一致も、連続問題の誤差上界や連続枝同一性の証明ではない。

## Case/native/Projectの版契約

専用Domainは `superfish_ng_planar_curved_domain`、domain_version=1。
必須keysはformat/domain_version/points_xy_m/cell_nodes/boundary_nodes。派生面積/owner/Jは入力で受け付けず再構築する。
平面Case版3は必須format/schema_version/name/model/geometry/mesh/numerics/modes/rf。
modelの全keys/値は既存平面と同じ。geometry.type=`quadratic_mesh`、geometry.domainが上の完全Domain。
meshはelement_order=2だけ。numericsはquadrature_order≥4、wall_quadrature_order≥4、max_geometry_boxes≥1の整数。
上限はarea/wall order32、box予算1e8。RFはstored_energy_j_per_m/conductivity_s_per_mの正の明示SI値。
未知keys/欠落/重複JSON keys、他のelement_order、穴/材料/βzの宣言はactionable error。

以下は将来版3の完全な合成TE入力例。TMでは内部自由度を持つ複数cellが必要であり、
この一cell例の偏波だけをTMへ変えて正モードを要求すると自由度不足を拒否する。

```json
{
  "format": "superfish_ng_planar_case", "schema_version": 3,
  "name": "synthetic quadratic xy patch",
  "model": {"physics": "rf_eigenmode", "coordinates": "cartesian", "polarization": "te",
    "propagation_constant_per_m": 0, "material": "vacuum", "boundary": "pec"},
  "geometry": {"type": "quadratic_mesh", "domain": {
    "format": "superfish_ng_planar_curved_domain", "domain_version": 1,
    "points_xy_m": [[0,0],[0.02,0],[0,0.02],[0.01,0.001],[0.01,0.01],[0,0.01]],
    "cell_nodes": [[0,1,2,3,4,5]], "boundary_nodes": [[0,1,3],[1,2,4],[2,0,5]]}},
  "mesh": {"element_order": 2},
  "numerics": {"quadrature_order": 8, "wall_quadrature_order": 12, "max_geometry_boxes": 100000},
  "modes": 1, "rf": {"stored_energy_j_per_m": 1, "conductivity_s_per_m": 58000000}
}
```

nativeのCase/result/manifestはschema_version=3。五ファイル名は既存平面と同じ
case.json/mesh.npz/fields.npz/results.json/manifest.jsonで、旧版1/2の集合・再生を保つ。
mesh NPZ版3はpoints_xy_m/cell_nodes/boundary_nodes/boundary_cells/boundary_local_edges/free_dofsのみ。
field NPZは元scalar係数と正周波数。elementの六geometry節点が六field DOFであり、
描画用に作る直線三角形をtrianglesや元geometryとして保存しない。
結果は曲線面積、完全外周/積分order、TE核と代数診断、全RF/phasor/J/m/N/Aを明示する。
readerは同じDomain/CaseからJ/K/M/拘束を再構築し、lowest正スペクトル・係数・全RFを物理再検証する。
hash一致だけ、あるいは少ない残差だけで完了にしない。再hashしたmid/周波数/係数/結果改変も拒否する。

PlanarProjectのformat/display unitを保持し、内側Case版3で曲線を区別する。
P08でCLI/API/Job/独立Study/GUI・元場プローブ/二次壁表示を接続し、別APIとの全配列/RF一致、
実中止/新サーバー、旧版1/2再生を受け入れる。GUIの表示単位変更は保存SIを変更しない。
P09の比較/調整は完全元Domain/場・写像/参照分割・予算を保存し、最終細分で境界を再投影しない。
未確認群/予算超過は周波数評価nullで停止し、新所有出力へ再開する。curve接続前の機能を先に宣伝しない。

## 条件別受入と後続の責任

| カード | 成立させる証拠 | P05現在の状態 |
| --- | --- | --- |
| P05 | 本仕様の範囲/全入力/gate/保存版、数式・出典/依存監査 | 2026-10-02仕様受入。製品ソース不変、FEM未実行 |
| P06 | 全Jacobian/全域、Green/面積/長さ、patch、直線K/M、TE核/TM正値 | 未実装/未受入 |
| P07 | 上の円二尺度/両偏波/三水準f/E/H/G、楕円/角対照、独立RF/増次数 | 未実装/未受入 |
| P08 | native/Project/CLI-worker/Study/GUI、全元場/RF、改変/中止/再起動/旧再生 | 未実装/未受入 |
| P09 | 固定二次領域/宣言写像、比較/ID回復、円/非円形調整両gate、所有保存/再開/GUI | 未実装/未受入 |

P05の検証は仕様/出典/JSON例/links/カード依存と解析対照の独立数値積分に限定する。
新規参考式16組（円半径2、TE4群/TM4群）についてBessel norm/エネルギー等分配/壁G/符号curl/尺度則を照合した。
raw driverと結果は `out/p05-planar-curved-spec-20261002/`。新固有値問題は解かない。
この数式確認をP06〜P09のFEM・保存・GUI受入へ水増ししない。

独立照合は終了0。最大相対差はBessel面積norm/全エネルギー/壁Gが各6.662e−16、
等分配8.882e−16、中央差分の符号curl3.995e−10。参照gate 1e−11/符号curl 1e−7を満たし、
二尺度のf/G/振幅則も1e−12以内。六節点JSON例、二尺度patchの面積/一次momentと
独立Green境界積分を1e−12で確認した。全123カードの重複なし/依存DAG/節IDと入口リンクを監査し、
前後395製品ファイルhashが一致。文書だけの変更のためunittest/seed/全validateは実行しない。
patch一次moment最大相対差5.552e−16、Green面積差0。リンク20件もPASS、仕様監査は2.647秒/終了0。
初回は四段見出しH09-aを二段限定で探索した監査器の誤りで終了1。
heading検査だけを全段対応へ修正し、失敗logを保持して再監査した。製品変更/数値再計算はない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python out/p05-planar-curved-spec-20261002/check_reference.py
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python out/p05-planar-curved-spec-20261002/check_spec.py
git diff --check
```

driverとJSON/logはignoredの数式・仕様監査証拠であり、製品へ解析値を供給する経路ではない。
P05条件（xy/P2/弱形式/零空間/壁RF/保存、円のf/E/H/G・二尺度・両偏波、楕円・角の個別gate、
未対応物理の明示、幾何とFEM細分の分離）は本書の各節で充足した。次はP06の実装と独立検査。

既存自作のCartesian/局所P2数学を設計参照した。NISTと著者公開講義を数式のみ参照し、
本文/図/コードの転載なし、新依存/legacy参照なし。実装各カードで選択unitと専用validatorを実行し、
shared coreを変更する場合は影響範囲の追加回帰を選ぶ。最終の全計画監査/必要な全validateは別に保持する。
