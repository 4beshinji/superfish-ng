# 曲線Hφの同二次領域細分（H13-a、受入済み）

`refine_curved_hphi_geometry`は各元参照三角形を4分割する。元のP2座標・全外周/穴・軸役割を保持し、解析曲線へ再投影しない。返すのはnative幾何、直前の親への完全な有理数chart、scalar P1/P2 prolongation、幾何診断であり、新しい固有解・周波数・RFではない。

## 構築と丸め

元のP2節点を新しい頂点にし、共有辺は節点番号で管理する。各新中点は元二次多項式を有理数で評価してからbinary64へ一度丸める。共有辺の両親からの厳密評価が一致することを確認する。軸辺だけは既存nativeの直線軸中点規約（両端の平均）を保持する。

新しい全境界ループとnative幾何を再検証する。出力scalar次数は元と同じP1またはP2で、全共有DOFの補間行を有理数基底から構成する。軸DOFや正半径qの定数零空間を落とさない。triangles・DOF・pair予算を構築前に検査する。

一般のSI寸法では二次写像の厳密な子係数がbinary64で表せない。[H11の比較領域](CURVED_HPHI_COMPARISON.md)は、この場合だけ明示版2を使えるようにする。

- 版1は従来どおり`restriction_policy=exact`で、nativeの全係数まで厳密一致を要求する。要求の保存形式も維持する。
- 版2は`native_restriction=binary64_roundoff`を明示する。`same_vacuum`の前後参照領域は引き続き全P2座標が厳密一致しなければならない。
- native各6節点の各座標差δは厳密な有理数で測定する。許可する節点差は、その参照要素の座標絶対値の最大×8ε以下（ε=2⁻⁵²）。利用者が任意の幾何許容差へ変えるフィールドはない。
- 差多項式のBernstein制御値は、頂点でδᵢ、辺で`2δmid−(δᵢ+δⱼ)/2`。各座標の制御値最大絶対値が全要素内の座標差上限となる。上限がnative要素の最大座標幅×512εを超えれば、局所形状に対する丸め分解能が不足として拒否する。
- 上限のbinary64表示は外向きに丸める。subnormalや有理数1/3でも、表示値を真の上限より小さくしない。

reportは要素ごとの座標差上限、最大値、`exact_native_restrictions`、使用したpolicyを明示する。参照chartの全被覆は有理数で厳密だが、丸めたnativeを数学的に完全同一の二次係数とは呼ばない。面積/回転体積差も別に記録する。これは浮動小数点表現の検証で、物理誤差上界や曲面近似精度の証明ではない。

## 独立不変量と検証記録

`out/h13-refinement-20260921/before.log`では、非dyadic尺度0.7の独立体積一致を確認した後、旧厳密比較がnativeの丸め差を拒否することを再現した。その後、未実装の細分APIのimportで失敗（1.013秒、終了1）。旧要求の拒否を回帰として隠すのではなく、新しい明示policyを別版として追加する。

初期3件は15.977秒PASS、終了0。正半径/軸接続、2穴、P1/P2について、独立合成shearの面積・回転体積、定数場、`P.T M_f P = M_c`と`P.T K_f P = K_c`（相対1e-10）、軸DOF、q定数零空間を確認した。元参照領域の1 ULP変更、nativeの1e-8 m変更、不正要求、予算超過を拒否する。

追加2件は13.701秒PASS、終了0。二回細分したchartを元参照へ有理数で合成し、完全被覆と質量保存を確認した。zオフセット64 mの対照は、座標の絶対丸めだけでは小さく見えても要素幅に対して未分解となるため停止する。

関連`test_curved_hphi_comparison test_curved_hphi_field_overlap test_curved_meridional_geometry test_curved_hphi_fem`の21件は40.895秒PASS、終了0。幾何誤差上限の外向き表示と構築前予算検査の追加後、新6件と三水準診断の直接利用先2件を検査中。

実行は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules/cases>`。新モジュールは`test_curved_hphi_refinement`。既存のFEM・求積/物理許容差・seed TMを変更しない。新外部資料・依存・legacy参照なし。既存の二次幾何、有理数多項式、合成shearを使用した。

H13-aは幾何/空間の準備であり、曲線追跡・調整・保存/GUIの受入ではない。次はH13-bの質量射影、有限比較スペクトルと部分空間追跡。親H13は未完了。

最終の新6件は30.759秒PASS、終了0（`final.log`）。三水準のstrict要求・実f/場/RF/guardの直接利用先2件は191.090秒PASS、終了0（`convergence-consumers.log`）。関連21件後の数値変更は誤差上限の外向き表示と細分の構築前予算拒否だけで、元積分/物理式は不変。新6件をその後の実装で確認し、関連21件の成功証拠を再利用した。全handle終端。H13-aを受入、親H13/全goalは継続。全suite/seed/Hosted CI/GUIの受入とは扱わない。
