# 入出力仕様 v1

## 入力

UTF-8 JSON。トップレベル `schema_version:1` とgeometryは必須。
未知キー・重複JSONキー・不正な数値・未対応geometryを拒否する。
材料や境界を入力しなければ自動推定するのではなく、v1の仕様が真空/PECに固定されている。
`epsilon_r` や `boundary:PMC` などを追加するとエラーになる。

```json
{
  "schema_version": 1,
  "name": "pillbox",
  "geometry": {"type": "pillbox", "radius_m": 0.1, "length_m": 0.2},
  "mesh": {"nr": 32, "nz": 40},
  "solver": {"modes": 4},
  "rf": {"beta": 1.0, "conductivity_s_per_m": 58000000, "normalization_j": 1.0}
}
```

profile形状は `{"type":"profile","points_zr_m":[[0,0.05],[0.1,0.1],[0.2,0.05]]}`。
zは0から厳密に増加し、全rは正。点間のRは線形で、両端にPEC端板が付く。

| キー | 既定値 | 制約 |
|---|---:|---|
| name | cavity | 文字列。出力パスとして使わない |
| mesh.nr | 24 | 半径方向分割数、整数>=2 |
| mesh.nz | 32 | 軸方向の目安、整数>=2。各profile区間をceilで分割するため総数は増える場合あり |
| solver.modes | 3 | 正整数、節点数−1より小さい |
| rf.beta | 1.0 | 0<β<=1、一定速度 |
| rf.conductivity_s_per_m | 5.8e7 | 正の有限値、常伝導近似 |
| rf.normalization_j | 1.0 | 正の有限値、全蓄積エネルギー |

極端なアスペクト比・巨大/微小寸法・過大な節点数での数値安定性は保証しない。
case v1の範囲拡張では、入力移行と拒否条件をテストしてからschema_versionを更新する。

## コマンド

- `superfish-ng solve CASE --out NEW_DIRECTORY`
- `superfish-ng converge --levels 8 16 32 64 --out NEW_JSON`
- `superfish-ng --version`

終了コード: 0=成功、1=収束ベンチマークの合格条件未達、2=入力/ファイル/ソルバエラー。
既存出力への上書きは拒否。書込み途中の障害では部分ファイルが残る可能性がある。

## 出力

| ファイル | 内容 |
|---|---|
| case.json | 正規化後の実際の入力。pillboxもprofileに展開される |
| results.json | case hash、環境、規約、mesh規模、全modeのRF量 |
| modes.csv | 各modeを1行としてRF量を記録 |
| fields.npz | 下記の再読込可能なNumPy配列。pickle不要 |
| axis_001.csv等 | z [m] と符号付きEz quadrature [V/m] |
| mode_001.vtk等 | ParaView用の2D meridian三角形と場 |

NPZ:

| 配列名 | 形状 | 意味 |
|---|---|---|
| points_rz_m | (N,2) | r,z [m] |
| triangles | (T,3) | 0-based節点index |
| boundary_edges | (B,2) | 境界辺の節点index |
| boundary_tags | (B,) | axisまたはpec文字列 |
| boundary_cells | (B,) | 境界に接する要素index |
| axis_nodes | (A,) | z昇順の軸節点 |
| u_a_per_m2 | (N,modes) | Hφ/r、単位A/m² |
| frequencies_hz | (modes,) | 昇順の周波数 |

VTKは **x=r、y=z、z=0** に断面を埋め込む。物理3D軸とviewerの座標を混同しない。
Hφはpoint scalar、Eの円筒成分はcell scalar。Ephasorは−i倍した値。
ParaViewでEを表示する際はCell Dataを選ぶ。回転させる場合は円筒成分のベクトル変換が別途必要。
今回ParaViewアプリによる対話操作は確認していない。

RFキーの式はPHYSICS.md。
`*_estimate`は表面場の一次要素推定で、メッシュ独立な設計値を意味しない。
ゼロに近い加速電圧でピーク比が定義しづらい場合はnull。NaN/InfinityをJSONに保存しない。

結果の単位はキー名に含める。`q0`、`transit_time_factor_abs`、`epk_over_eacc_estimate`は無次元。
`bpk_over_eacc_estimate_mt_per_mv_per_m`は mT/(MV/m)。インピーダンスは全長に対するΩで、Ω/mではない。
