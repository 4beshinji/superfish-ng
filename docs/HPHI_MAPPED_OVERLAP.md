# 直線Hφの明示写像と独立FEM分割の交差（H09-a）

2026-09-21。`mapped_hphi_overlay(previous, current, mapping)`を追加した。
[H08の幾何対応](HPHI_GEOMETRY_MAPPING.md)を、内部・境界分割が異なる
元FEMメッシュへ適用する基盤である。H09全体の完了ではない。

## 契約

入力は二つの検証済み`MeridionalMesh`または二つの`AxisConnectedMesh`と
`HphiGeometryMapping`。両FEMメッシュは対応する写像端の外周/全PEC穴を
厳密に被覆する必要がある。FEM節点番号・要素番号/列の循環置換・境界分割・穴の列挙順は独立。
写像制御メッシュ間の明示対応はH08の契約を保持する。

1. 前FEMと前制御分割を交差させる。
2. 各交差片を対応する制御三角形の重心座標で変形先へ写す。
3. 写した全片と現FEMを交差させる。
4. 各最終片を元領域へ逆写像し、両側の元FEM重心座標を保存する。

binary64入力座標を厳密有理数として扱い、途中の交点・重心比・写像点も丸めない。
既存の四則演算による有理数クリッピングとBVHを再利用し、最後のquadratureデータだけfloatへ変換する。
前FEM全セル、前制御全セル、現制御全セル、写像後の全交差片、現FEM全セル、
最終逆写像による前FEM全セルの面積を、それぞれ有理数で完全一致検査する。

戻り値`HphiMappedOverlay`は既存のセル番号・重心座標・現領域頂点/面積行列式に加えて、
`mapping_cells`、`previous_vertices_rz_m`、`previous_determinants`を保持する。
全配列は読取専用。行列式は基準三角形からの面積倍率（面積はその1/2）。
回転体積は各側の実半径を用いた`2πr dr dz`であり、面積倍率だけで置換しない。

`max_candidate_tests`は最初のBVH探索にfloor(N/2)、次に残りを割り当てる。
両探索で節点/葉比較を数え、未使用予算を相互融通しない。
`max_overlay_triangles`は各入力、途中、最終のそれぞれに適用する。
超過・異領域・不正型・浮動小数点で未解像の非正行列式は例外で拒否し、部分結果を返さない。

このAPIは元場の再補間もFEMも行わない。E/H移送と重み、質量射影、guard/ID判断はH09-b、
要求/保存/CLIはH09-c、worker/GUIはH09-dで接続する。

## 受入証拠

新4件：

- 軸接続/正半径の穴移動（区分ごとに異なるJacobian）、逆写像、反対対角線の独立FEM分割。
- 二つの穴、一様尺度、節点/セル/穴の番号置換、追加の明示境界分割。
- 非二進小数の同軸寸法と独立内部頂点。`r_old*z_new`の回転体積積分を独立な矩形積分式と比較。
- 異領域/異軸型/不正写像/比較予算/最終要素数上限の拒否。

両側で`1,r,r³,rz²,r³z²`の矩形差による解析積分と一致し、全親セルの包含と元座標再構成を確認した。
一様尺度の点は2倍、面積は4倍、回転体積は8倍で、元データと比較した。
既存実装にこの非一様交差分割APIはなく、同一領域/一様尺度だけでは穴移動の比較を表せなかった。

初回は試験の境界中点が実節点でなく拒否された。既存境界節点による分割に修正後、
参照矩形式が追加頂点前の添字を仮定して2件FAILとなった。参照式を矩形のmin/maxへ修正した。
製品の幾何ゲート・物理許容差は変更していない。失敗ログは保持する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache \
uv run --no-sync --python .venv/bin/python python -m unittest -v \
  test_hphi_mapped_overlap test_hphi_geometry_mapping test_meridional_overlap
# 12件中、既存8件PASS、新規2件PASS/2件FAIL（試験参照式）。3.402秒、終了1。
# out/h09-a-overlay-20260921/tests.log

# 参照式修正後、変更した新規4件だけを再実行
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache \
uv run --no-sync --python .venv/bin/python python -m unittest -v test_hphi_mapped_overlap
# 4件PASS、1.514秒、終了0。
# out/h09-a-overlay-20260921/new-tests-corrected.log
```

以上は既存8件＋修正後新規4件の分割証拠であり、単一の全件PASSではない。
独立幾何APIのみの追加で、既存FEM/場/RF/seed経路に変更なし。seed/full validatorは実行していない。
新規外部資料・依存・legacy参照はない。合成形状の被覆/積分の証拠を
物理場の精度やモードIDの確認へ拡張しない。
