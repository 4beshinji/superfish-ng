# 平面磁場の有限多極表現・座標変換

2026-09-13 JST。固定829sourceを主835sourceへ統合し、専用API範囲で限定受入。

[受入計画](PLANAR_MAGNETIC_MULTIPOLES_PLAN.md)に従い、PlanarMagneticMultipoleFrame/Seriesを追加した。局所By+iBx、normal+i*skew[T]、n=1..32、明示した原点[m]・半径[m]・反時計回り角[rad]を保持する。有限多項式の評価と二項展開による原点/半径/回転の変換を行う。来歴、零場、厳密JSON規約を保存する。元FEM場の抽出と力/トルクはこの段階に含まない。

規約は[CERNのField Error Naming Conventions for LHC Magnets、LHC-M-ES-0001 rev3.0、2001-10-24、§§2.1/2.3/2.4/5.1/5.2](https://lhc-div-mms.web.cern.ch/tests/MAG/FiDeL/Documentation/lhc-m-es-0001-30-00.pdf)に照合した。局所座標と物理ベクトルの回転を別に導出し、Cn' = exp(i n Δθ)(R'/R)^(n−1) Σj≥n binom(j−1,n−1) Cj δ^(j−n)、δ=exp(−iθ)(c'−c)/Rを用いる。LHC固有の基準半径、10^-4単位、磁石長の積分は導入しない。資料のコード・図表・磁石データは再利用しない。

最初に有限半径R=1e-320の単位四極場をx=Rで評価すると、解が有限でも複素除算の中間逆数で失敗した。実座標をRで先に割ってから複素化する修正を行い、R=5e-324から1e300の対照も追加した。演算が解像できない場合は拒否し、許容差は不変。最初の失敗、修正前コード、判断はout/planar-magnetic-multipoles-development-20260913に保存した。

追加5unitは0.007秒でPASS。独立84条件は5.947738秒でPASS。次数1/2/3/5/8/16/32、角0/.3/−.7、半径.01/.2、振幅1/−7を組み合わせ、Decimal60の独立Cartesianべき評価84比較、Fourierによる新frame係数168比較、逆変換168比較、合成84比較、div/curl差分168比較を行った。最大相対差は元場1.709e-16、変換後場4.497e-16、Fourier係数2.049e-15、逆変換4.549e-16、合成3.763e-16。差分div/curlは1.943e-10/1.666e-10。計画の1e-11/2e-6を満たした。

固定sourceと証拠はout/planar-magnetic-multipoles-development-20260913、独立報告はout/planar-magnetic-multipoles-independent-trial-20260913/report.json、標準はout/validation-planar-magnetic-multipoles-candidate-20260913。検証用の合成多項式であり、実測構造・FEM求解・無源領域の認証ではない。新規依存・旧版実行なし。

標準2751.003秒、1313合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主5unitは0.007秒でPASS。標準/独立の固定829sourceと主835source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
