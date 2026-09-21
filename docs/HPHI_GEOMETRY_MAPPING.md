# Hφの直線幾何対応（H08）

2026-09-21。`hphi_geometry_mapping.py`の幾何API。追跡・調整への接続はH09。
既存の一様尺度比較と調整要求版1は変更しない。

## 対応の宣言

`coaxial_dimension_mapping(previous, current)`は二つの`CoaxialCase`から、
内半径a、外半径b、長さLを対応させる。

```
r' = a' + (r-a) (b'-a')/(b-a)
z' = z L'/L
```

座標はm、Jacobianは無次元。二つの三角形で矩形全域を被覆する。
この幾何分割は両側のFEMメッシュのnr/nzに依存しない。

`HphiGeometryMapping(previous, current)`は二つの`MeridionalMesh`または
二つの`AxisConnectedMesh`を受け取る。頂点番号・三角形の順序と接続・境界辺・
境界成分番号・境界線分番号を明示的に共通にする。これは自動対応ではない。
両側の形状と三角形を既存readerで再検証するため、全境界/全領域被覆、穴の個数、
非交差、連結性、正Jacobianが必要である。対応軸頂点と順序も保持する。
未知の点対応や穴の消失、反転、未被覆、軸をr>0へ移す変形は拒否する。
任意の別FEM分割との交差分割・場移送はH09で接続する。

`jacobians`は各三角形の`d(r',z')/d(r,z)`、`inverse()`は逆対応を返す。
`map_in_cells(cells, barycentric)`は明示した親要素と非負・和1の重心座標で評価する。
物理積分の測度は変形先の`dr' dz'`、回転体積では`2πr' dr' dz'`である。
面積Jacobianだけを回転体積の倍率としない。

## 加速座標

軸接続では`transport_axis_coordinates`を明示して使用する。
元軸上の端点/位相原点を、対応軸辺上で区分一次に移す。
軸区間外の位相原点は外挿せず拒否する。この限定APIから、任意の位相原点を持つ
既存Case全体の非一様変形対応を主張しない。beta・規格化・場・RF量は計算/変更しない。
正半径領域へ加速軸を推定して追加しない。

## 検証

新規4unitで同軸非相似の解析面積`(b-a)L`、体積`π(b²-a²)L`を
元三角形上の独立積分と比較する。穴の位置を変える区分アフィン例は
外円筒から穴の回転体積を引いた式で検査する。一様尺度は既存H02の
`_scaled_mesh`と全幾何辞書一致、面積s²・体積s³、軸座標sを確認する。
逆写像、穴消失・反転・未被覆・軸移動・不正重心座標も検査する。
新API実装前は非一様対応APIがなく、既存一様尺度を代用しないことを確認した。
初回の逆Jacobian積のゼロ成分検査は絶対許容差0のため2.22e-16で失敗した。
新設のこの代数検査だけをbinary64の4εへ修正した。既存物理ゲートは不変。

新規4件と既存22件の計26件が22.178秒でPASS、終了0。
実行記録: `out/h08-geometry-20260921/tests.log`。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache \
uv run --no-sync --python .venv/bin/python python -m unittest -v \
  test_hphi_geometry_mapping test_axis_connected_mesh test_hphi_mesh test_axis_hphi test_hphi_study
```

seed TMの利用経路・FEM/場/RF核は変更せず、seed/full validatorは対象外。
新しい外部資料・依存・旧コード/バイナリの参照はない。合成形状の幾何検証であり、
場の同一性、数値解の精度、連続モード枝の証明ではない。
