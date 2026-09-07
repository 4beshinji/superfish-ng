# 境界タグ付き非構造三角形入力

2026-09-07、P0-02/P0-03。CLIとPython APIから外部で作成した三角形メッシュを使える。
既存の真空・軸連結m=0 TMとCase輪郭の範囲に限定する。
この機能は任意CAD・穴・内導体への対応ではない。外部メッシャー依存は不要。

```bash
python -m superfish_ng solve case.json --mesh mesh.json --out out/external-new
```

`--mesh`を明示するとCaseのnr/nz・triangulation・局所細分による生成を置き換える。
形状、端面境界、モード数、RF条件はCaseから使い、メッシュの境界と照合する。
GUI・Project・Studyからのメッシュ指定はこの段階の対象外。
Gmshなどの独自形式を直接読む機能も未実装。

## mesh schema v1

全キー必須で未知キー・重複JSONキーはエラー。単位はm、座標順は(r,z)、添字は0始まり。
以下は半径0.08 m・長さ0.12 mの円筒断面を中心節点へ4分割する最小例であり、
精度検証済みメッシュではない。実計算には細分収束が必要。

```json
{
  "schema_version": 1,
  "length_unit": "m",
  "coordinate_order": "rz",
  "index_base": 0,
  "points": [[0, 0], [0.08, 0], [0.08, 0.12], [0, 0.12], [0.04, 0.06]],
  "triangles": [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]],
  "boundary_edges": [[0, 1], [1, 2], [2, 3], [3, 0]],
  "boundary_tags": ["pec", "pec", "pec", "axis"]
}
```

三角形は(r,z)面で反時計回り。境界辺の向き・節点番号・要素番号は任意。
タグはaxis/pec/electric_symmetry/magnetic_symmetry。PECを含む全境界辺を明示し、
内部辺を含めない。軸はr=0、端面はz=0またはCase.lengthに一致させる。
接線円弧の場合はCaseのchord_tolerance_mで定義した既存の折れ線を使う。
異なる弦分割を自動的に同一円弧だと推定しない。

有限座標、非負半径、整数添字、重複節点/要素、孤立節点、正のJacobian、
共有辺の向きと接続数、境界の次数、連結性、Euler数、境界輪郭・周長・面積を検査する。
タグを推測したり三角形の向きを黙って直したりしない。
軸はタグ付き辺から単一チェーンを確認し、z順へ並べた節点から電圧を積分する。
壁損失とピーク場に必要な境界の隣接要素は実際の接続から再構成する。

## APIと保存

```python
from superfish_ng import Case, solve
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.mesh import make_mesh
from superfish_ng.io import save_run

case = Case(((0., .08), (.12, .08)), modes=1)
data = mesh_to_dict(make_mesh(case))  # または外部メッシャーの同じschemaのdict
solution = solve(case, mesh_data=data)
save_run(case, solution, "out/mesh-api-new")
```

保存先にmesh.jsonを追加し、results.jsonのmesh.input_sha256にcanonical JSONのSHA-256を記録する。
case_sha256だけで外部メッシュを区別しない。mesh.generation_parameters_applied=falseを記録する。
`read_solution`はmesh.jsonのhashとfields.npz内の節点・接続・タグ・軸・隣接要素の一致を確認する。
`--reflect-full`も対応し、鏡映後の全領域メッシュを保存する。元の半領域Caseは既存通り記録する。
通常のメッシュ生成経路と既存出力は変更しない。

## 受入結果

1. 同一メッシュの節点・要素・境界辺番号を乱数で入れ替え、周波数・R/Q・G・Vacc・Epkが
   相対1e-9以内で不変。軸とPECの取り違え、磁気対称面の欠落は拒否。
2. 乱数で内部節点をずらしたDelaunayメッシュで円筒TM010を3段階計算。
   解析値に対する相対誤差は次表。周波数1e-4、RF 0.005の基準を最細で満たす。
3. 不正入力の拒否、保存再計算、改変されたmesh.jsonの拒否、CLI、半領域の本質境界と
   全領域鏡映、既存出力の上書き拒否を検査。

| 分割目安n | 周波数相対誤差 | R/Q相対誤差 | G相対誤差 |
|---|---:|---:|---:|
| 16 | 1.6028e-5 | 8.8776e-3 | 4.1823e-5 |
| 32 | 4.1554e-6 | 2.7733e-3 | 1.0922e-5 |
| 64 | 1.0429e-6 | 8.2782e-4 | 2.8027e-6 |

新規7 unittest合格。全suiteは114件中112件合格・NGSolve環境専用2件skip。
`out/validation-mesh-input-20260907/`の標準数値検証PASS。
seedの円筒6モード・shaped 3モードに対する周波数差ゼロ、RF相対差最大6.67e-16。
ベンチマーク・許容値の更新なし。
P0-03に関連する軸積分と壁積分は既存実装を維持し、非構造接続で成立することを確認した。
表面ピークの新しい誤差保証、高次要素や一般モード追跡の追加ではない。
