# 曲線Hφの元Project形状変数（H13-cの途中段階）

`CurvedHphiShapeLaw`は全P2幾何節点に対する変位を明示し、元の`HphiProject(CurvedHphiCase)`から候補を独立に生成する。頂点だけの直線変形ではなく、辺中点の変位も入力で指定する。返す`CurvedHphiShapeResult`は候補Project、完全二次比較domain、形状診断を保持する。

この段階は形状生成まで。調整探索、元場のID追跡/回復、同じ二次領域での最終細分、粗細周波数差と目標の別判定への接続は残っており、H13-cは未完了。

## 形状と軸の契約

要求版1は`full_quadratic_displacement`、正の無次元reference値、元P2節点数と同じ有限SI変位配列、`transport_on_axis`の加速座標方針を持つ。各候補も正の無次元値を指定する。全座標は`x_original + (value-reference_value)*displacement`を有理数で評価してからbinary64へ一度丸める。直前候補に変位を累積しない。元Projectをコピーし、FEM次数・求積・モード数・エネルギー・導電率・表示単位を保持する。

元の全境界頂点を明示した参照角として宣言し直す。これにより、元の直線境界の途中にある節点も移動できる。参照側の全P2座標とセル係数は元と同一で、全穴/軸を保持する。元と再宣言後の境界segment番号を診断に記録する。候補との対応は全二次domainで検証し、不正向き・交差・穴や軸の破壊を受け入れない。

軸上の全頂点・中点で半径変位は厳密に0、中点変位は両端変位のbinary64平均と一致しなければならない。候補軸中点には既存native規約の「候補両端座標の平均」を適用する。名目有理数座標との差を測定し、最大絶対座標×8ε以下、かつ各軸辺の寸法×512ε以下を要求する（ε=2⁻⁵²）。上限表示は外向き丸め。局所寸法で分解できない差は拒否し、利用者が任意許容差で回避するフィールドは設けない。

加速経路がある場合、元軸の対応区間で端点と位相原点を全て移送し、betaを保持する。native軸は辺ごとに厳密直線なので、この移送は元の軸頂点に基づく区分線形対応になる。経路の推測・座標の固定・軸外への外挿は行わない。周波数補正、RF再正規化、モードIDの推定は形状APIの役割ではない。

## 検証記録

証拠は`out/h13-curved-shape-20260921/`。`before.log`は元曲線qのFEMを解いた後、新形状APIのimportで失敗（1件、0.602秒、終了1）。既存FEMの数値誤答ではなく、機能欠落のred。

`after.log`は初期3件、8.234秒、終了0。q/u・2穴の全P2二倍尺度について、独立面積4倍/体積8倍、実FEM周波数1/2、全節点/元Project不変を確認。二次shearの面積/体積保存、加速端点/位相原点の移送、beta保持、厳密要求・不正形状/軸変位/節点数の拒否も検査した。

局所軸丸めの拒否を追加後、`test_curved_hphi_shape_tuning test_hphi_geometry_mapping test_curved_meridional_geometry`を検査する。新しい対照は1e12 mの軸オフセットで、絶対丸めが小さく見えても辺寸法に対して未分解なら拒否する。軸外位相原点の外挿拒否も確認する。

実行は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules>`。既存FEM/seed TM/物理許容差は変更しない。全suite・調整・所有履歴・GUIの受入ではない。

既存の曲線幾何、有理数評価、直線境界cycle展開、明示軸座標移送、合成shear不変量を使用した。新外部資料・依存・legacy参照なし。合成形状を測定構造とは扱わない。

`final.log`：局所軸丸め検査を追加した最終実装で、新4件と関連9件の計13件、11.866秒、終了0。全検査handle終端。成功後の数値変更なし。H13-cは調整/追跡/回復/最終細分の接続まで継続する。

2026-09-21追記：[探索/最終/比較候補の元領域保持](CURVED_HPHI_TUNE_TRIALS.md)を接続。曲線調整runner・ID回復は引き続き未完了。

2026-09-22追記：[曲線調整runnerと明示ID回復のH13-c監査](CURVED_HPHI_TUNING.md)を完了した。所有保存/履歴/CLI-worker/GUIのH13-d/eと親H13は未完了。
