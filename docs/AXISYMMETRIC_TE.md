# P01: 真空・軸接続m=0 TE

[TE鏡映結果の収束比較](TE_REFLECTED_CONVERGENCE_PLAN.md)を接続・限定受入。同じ元半領域の物理・対称条件だけを比較し、電場/磁場/RFの個別判定と部分スペクトル番号を保持する。独立12FEM、4Study、Chrome7操作、CLI/GUI保存一致と再起動を確認。標準795件（793合格、2skip）と既存TM/TE数値回帰が合格。

2026-09-09追補: [TE対称面鏡映](TE_REFLECTION_PLAN.md)を接続。TEのEφは磁気対称面で偶、電気対称面で奇、Hrは逆符号、Hzは同符号。元振幅を維持しU/PEC損失は2倍、f/Q0/Gは不変。専用native版4で元半領域から再構成・再検証し、API/CLI/Project/Job/GUIで部分スペクトルと明示する。鏡映結果の追跡は未対応。収束比較は上記の元半領域方式に限定対応。標準790件（788合格、2skip）と既存TM/TE数値回帰まで限定受入済み。

2026-09-09追補: [通常TE GUI](GUI_TE.md)の場表示・プローブ・偏波選択を接続。Chrome10項目と保存場/独立球形解析の照合が合格、最終標準766件・既存TM/TE回帰も合格。以下の初期実装時のGUI保留記録とは区別する。

後続の[TE Project/JobManager](TE_JOBS.md)を接続。以下の初期実装時の未接続範囲は、この後続仕様で更新する。

追補: [曲線P2のTEとnative版3](CURVED_TE_PLAN.md)を追加。以下は直線P1/P2版2の規約と当時の受入記録。曲線版の場・壁積分・実二次幾何の保存は追補を参照する。

2026-09-09、基準b0f8b0c。追加物理を明示するP01の数式・入力・保存契約。

## 物理と離散化

時間依存は `exp(+iωt)`、SI、ピークphasor。電場を実振幅 `Eφ=r v` とし、他の電場成分はゼロ。
Maxwellの `curl E=-iωμ0 H` から磁場は `+i` 倍の実振幅

\[
H_{r,q}=-\frac{r\partial_zv}{\omega\mu_0},\qquad
H_{z,q}=\frac{2v+r\partial_rv}{\omega\mu_0}.
\]

軸ではvを有限に保ち、`Eφ=Hr=0`、`Hz,q=2v/(ωμ0)`。vを軸でゼロ拘束しない。
点検索の逆写像の丸め誤差があっても、指定座標r=0にはEφ/Hrの厳密な正則値を返す。

弱形式は

\[
K_{ij}=\int r[(2N_i+r\partial_rN_i)(2N_j+r\partial_rN_j)
+r^2\partial_zN_i\partial_zN_j]drdz,\quad
M_{ij}=\int r^3N_iN_jdrdz,\quad Kv=(\omega/c)^2Mv.
\]

このスカラーcurl積分は既存自作のP1/P2積分核と共通だが、境界と物理未知数は異なる。
PECと電気対称面でv=0を必須条件とし、平坦z磁気対称面には自然条件 `∂z v=0` を課す。
TMのPEC自然条件で代用しない。直線三角形のP1/P2で解き、自由行の残差を確認する。
残差が小さいことはFEM誤差が小さい証明ではない。

`U=ε0/2 ∫|E|²dV=πε0 vᵀMv` によって指定された全蓄積エネルギーへ規格化する。
電気/磁気エネルギーはそれぞれ `ε0/4 ∫|E|²`、`μ0/4 ∫|H|²` として別計算する。
壁損失はPEC辺だけの `P=Rs/2 ∫|Ht|²dS`、`Rs=√(ωμ0/(2σ))`。
対称面を壁へ含めず、GとQ0を返す。表面積分は5点Gaussで直線P1/P2多項式を積分する。
Vacc/Eacc/TTF、両R/Q、Epk/Eacc・Bpk/Eaccはnullと理由を保存し、軸加速量を捏造しない。

## 入力・操作

Case schema_version 3で既存のmodel中の `polarization` を `te` にする。
physics=rf_eigenmode、coordinates=axisymmetric、azimuthal_index=0、単一vacuum/interiorは必須。
旧v1/v2は暗黙TMのままで、旧JSON/hashを変更しない。

```sh
superfish-ng solve examples/te/pillbox.json --out out/te-example-new
superfish-ng replay-te out/te-example-new
```

例題は合成円筒であり、KEK/LANLの実測形状ではない。Pythonは通常の `solve(case)`、
`rf.quantities(case, solution)`、`io.save_run(case, solution, out)` を使える。
場は `TEFieldSampler(solution).evaluate(points_rz_m, mode=0)` または `FieldSampler.from_solution`。
`Ephi_V_per_m`、`Hr_quadrature_A_per_m`、`Hz_quadrature_A_per_m` を返し、磁場phasorは`+i`倍である。
通常のTMの3成分タプルを返すcell_fieldsはTEを拒否する。
外部タグ付きメッシュは通常の `solve --mesh` に対応し、mesh_from_dictでCaseと照合する。

対応範囲は軸接続・真空の直線三角形P1/P2。geometry_order=2のTE、Project/JobManager/GUI、
反射による場構築、TE追跡/Study/最適化は未接続。未対応入口はTEをTMとして計算/読込せず拒否する。
Project/GUIの統合はO02を含む後続工程。TEのactive length/voltage interval/phase origin指定は拒否する。
betaは従来のCase項目として保持されるが、TEの加速量はN/Aなので数値評価には使わない。

## TE native保存

結果schema_version=2、physics=axisymmetric_m0_te、係数は `coefficients_v_per_m2`。
TMのu_a_per_m2を再利用しない。case.json・mesh.json・fields.npz・results.json・modes.csv・
モードごとのaxis CSV/VTKを出力し、最後に `te_complete.json` をno-replaceで公開する。
VTKは元三角形の中心値で、P2の表示細分や平滑化・ピーク保証を意味しない。

`te_saved.read_te_run` は完了/全必要ファイルのhash・リンク拒否、Case/メッシュとfield_space、
phasor/規格化、PEC必須係数、自由行FEM残差、質量直交性、保存場からのRF量の再計算を確認する。
再読込で固有値問題を解き直さない。CSV/VTKはファイルの完全性、数値の再検証はNPZの係数に対して行う。
TMのread_solutionはTE宣言/TE形式を拒否する。TE宣言に旧TM係数・旧保存形式を組み合わせても拒否する。
旧読取機は新結果版/TEモデルを受理しないので、場の単位と成分を混同しない。

## 独立受入条件

円筒の正の `J0′(χ)=0`（`J1(χ)=0`）と軸方向整数p≥1から
`f=c/(2π) sqrt((χ/R)²+(pπ/L)²)` を用いる。零点χ=0はTE空洞共振として数えない。
正則なEφ、Hr、HzのBessel形をMaxwellから別に評価し、電場との共通符号だけを対応付ける。
Hzがゼロとなる点などは成分全体の最大振幅で誤差を規格化する。
周波数式・導関数零点の公開参照は [Fitzpatrick, Cylindrical Cavities, 式1351–1353](https://farside.ph.utexas.edu/teaching/jk1/lectures/node116.html)（R35）。
参照の時間phasorをそのまま流用せず、上記の+時間phasorから磁場符号を導出した。

6モード・2尺度のP1/P2細分で、f相対差1e-4、各場成分1%、G相対差0.5%、エネルギー釣合い1e-9を目標とする。
入れ子メッシュでのRitz周波数減少、Maxwell相似f/G/Q0、P2のCLI/API/native一致を別々に確認する。
P1/P2の保存/CLIはunitでも確認する。円筒以外の一般形状精度や曲線TE/O02全体の受入へ広げない。

## 初回の反例と修正

旧TMのPEC自然条件はTE011解析値に対し約41.93%差で、同じ境界の流用が失敗することを確認した。
初回TE unit4件は軸Eφ/Hrの微小な丸め値で1件FAIL。正則軸値を明示し、許容差を変えず4件PASS。
旧TM nativeにTE宣言を入れてhashを更新すると旧readerが受理する反例も確認した。
Case読込直後のTE拒否を追加し、回帰テストへ組み込んだ。新しいTEモデルを許可したために
古い形式を誤読する経路を閉じる修正であり、旧TM形式の解釈を変更しない。

最初の独立検証 `out/te-independent-20260909` は対角P1のn=256でfは合格したが、
場最大約1.83%、G最大約1.09%で未達だった。失敗log/driverを保持した。
交差分割n=256の追加観測でも一部未達のため、最終受入には用いない。
同じ対角格子のn=256→768の実細分で条件を満たした。許容差は維持した。
次の独立実行 `out/te-independent-accepted-20260909` はP1両尺度で合格したが、
P2 n=32の高次モードのG最大約0.999%で未達だった。部分結果と失敗log/driverを保持し、
n=64の追加対照を経て、最終版では両次数・両尺度を再実行した。
最初の標準実行 `out/validation-te-20260909` はTE/TM誤読の修正のため明示中止し、interruption.jsonを保持した。

## 最終独立検証

`out/te-independent-final-20260909` は6モード・2尺度についてP1の32/64/128/256/768、
P2の8/16/32/64分割を新規計算した（18回のAPI FEMと2回のP2 CLI FEM）。
終点の全モードで事前のf/場/G/エネルギー条件がPASS。P2のCLI/APIの係数・RF量、
native再読込の係数も一致する。途中の未達メッシュは収束履歴に残している。

| 項目（2尺度・6モード中の最大） | P1最終 | P2最終 |
|---|---:|---:|
| 係数数（拘束前） | 886657 | 24897 |
| 周波数相対差 | 7.861e-6 | 3.509e-7 |
| 場成分の相対差 | 5.148e-3 | 1.492e-3 |
| G相対差 | 3.690e-3 | 2.505e-3 |
| 電気/磁気エネルギー比の差 | 1.599e-12 | 7.572e-14 |

Maxwell相似f/G/Q0の差は最大1.219e-12。一般形状の精度保証・FEM誤差上界ではない。
局所の場精度/壁損失は周波数より遅く収束する。例題のP2格子は64/96にした。
保存済み検証値から作成した `convergence.png` と描画driverも同じoutに保持する。
図の周波数・G・場成分の各収束曲線と受入線を目視確認した。

最終のTE unit7件は0.302秒でPASS。外部メッシュの通常solve経路で周波数/係数/RFが一致し、
共通FieldSamplerがTEの成分名を返すこと、不正タグを拒否することも追加確認した。
TE保存にはソフトウェア版とPython/NumPy/SciPy/OS情報を記録する。
再読込のRF量照合は浮動小数点再積分の丸めのため相対1e-10とし、
ケース・成分名・null・mode index・phasor規約は厳密に検査する。これは物理精度の許容差とは別である。

最終標準 `out/validation-te-final-20260909` は750件中748合格・2skip（1150.683秒）、
標準convergeもPASS。seed9モード19量の周波数差は0、RF/エネルギー最大差8.882e-16。
最終標準・上記独立検証・終了後436ソース/テスト/スクリプト/例題のhashが一致した。
初回中断と中間標準749件は保持し、最終版の証拠と混同しない。
