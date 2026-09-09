# 単純多角形の平面TE/TM遮断問題

[平面表示/GUI](GUI_PLANAR.md)も接続・限定受入。以下は保持するProject/JobまたはFEM/nativeの契約と当時の検証記録。Study/追跡等は後続。

[専用Project・ローカルジョブ](PLANAR_JOBS.md)を追加し限定受入。以下は保持する平面FEM/単体native・CLIの契約。

専用Case版2により、真空・単一PEC多角形・明示xy三角形のP1/P2をsolve/replay/probeへ接続した。2026-09-10、主ツリーの独立物理検証・標準回帰まで限定受入。矩形のCase/native版1を保持する。[受入計画・隔離検証](PLANAR_POLYGON_RF_PLAN.md)、[メッシュ契約](PLANAR_POLYGON_MESH.md)。

## 使い方

```
python -m superfish_ng solve-planar examples/planar/triangle_te.json --out out/my-triangle-te
python -m superfish_ng replay-planar out/my-triangle-te
python -m superfish_ng probe-planar out/my-triangle-te --points points.json --mode 1 --out out/my-triangle-probe.csv
```

TM例は `examples/planar/triangle_tm.json`。例題は合成した直角二等辺三角形の粗い操作例で、測定構造や全物理精度の認証例ではない。`points.json` はメートル単位の `[[x,y],...]`。例えば `[[0.10,0.03],[0.15,0.10]]` はこの三角形の内部にある。出力は新規ディレクトリ/ファイルに限り、probeのCSVをnativeディレクトリ内に作成しない。

Pythonでは `PlanarMesh.create(polygon_xy_m, points_xy_m, triangles)` で元メッシュを検証し、`PlanarPolygonCase(mesh, polarization='te', element_order=2, modes=4)` を `solve_planar` へ渡す。JSONの読込は `load_planar_case` が版を振り分ける。従来の `PlanarCase` とその `from_dict/load` は矩形版1のまま、軸対称の `Case` は平面入力を拒否する。

## Case版2

トップレベルは `format=superfish_ng_planar_case`、`schema_version=2`、`name`、`model`、`geometry`、`mesh`、`rf`、`modes` を全て要求する。

| 節 | 必須内容 |
|---|---|
| model | physics=rf_eigenmode、coordinates=cartesian、polarization=teまたはtm、propagation_constant_per_m=0、material=vacuum、boundary=pec |
| geometry | type=polygon、vertices_xy_m=反時計回りの角点配列。終点を重ねない |
| mesh | points_xy_m=明示した元節点、triangles=正向きの整数番号三つ組、element_order=1または2 |
| rf | stored_energy_j_per_m、conductivity_s_per_m。有限の正数 |
| modes | 最低の正固有値からの要求数。正整数 |

多角形の角点は元メッシュに同じ座標で存在し、境界が宣言辺を完全に被覆する必要がある。節点/要素番号を保持して再組立する。余分なキー、暗黙の単位変換、材料、曲線、穴、非PEC境界、伝搬、TEMを受け入れない。メッシュの面積一致だけで重なりや欠損を許可しない。

capabilitiesの `planar_cutoff.schema_versions` と `geometries` が対応一覧を返す。従来の単数 `schema_version=1` と `geometry=rectangle` は矩形の既定生成経路として保持する。

## 物理・点検索

矩形と同じ面積K/M、TMの実EzとDirichlet壁、TEの実HzとNeumann壁・定数零空間除外を用いる。全real/quadrature E/H成分、ピークphasor、単位長U′[J/m]・側壁損失P′[W/m]を保持する。有限長の端面や加速経路はなく、二つのR/QとVacc/Eaccは理由付きN/A。モード番号は順位であり、モード名や追跡済みラベルではない。

点検索は実際のbinary64三角形への所属を厳密な方向符号で確認する。共有辺・頂点では最小の元要素番号を選ぶ片側評価で、要素間の不連続な派生場を平均しない。薄い要素に固定のbarycentric許容差を使って外点を入れない。意図した直線上の座標でも、丸めた結果が実メッシュ外なら拒否される。現方式は一標本ごとに全要素のAABBを調べるため、大規模なprobe/描画の性能受入とはしない。

## nativeと検証

五ファイル（case.json、mesh.npz、fields.npz、results.json、manifest.json）を保持し、多角形はmanifest/result版2を使う。Caseとmanifestの版一致、hash、宣言形状・元メッシュ・全FEM配列、最低正スペクトル・係数・単位長規格化・RFを再検証する。保存係数を新しく解いた別の基底に置換しない。読込中のファイル変更を拒否する。矩形版1の再生は同じ経路で維持する。

独立物理検証は次のコマンドで新規outへ実行する。P1の高位モードでは大きな細分が必要で、既定の全検証には時間を要する。

```
OPENBLAS_NUM_THREADS=1 python scripts/validate_planar_polygon.py --out out/my-polygon-validation
```

既定は三角形の両尺度・TE/TM・4モード、P1 n32/96/448、P2 n16/32/64。解析のf、スカラー場、派生E/H、三辺の閉形式壁積分Gを分け、最終の相対f1e-4・場1%・G0.5%で判定する。粗分割で未達なら非零終了し、結果を保持する。代数残差や隣接メッシュ差を絶対誤差保証とはしない。

Project/Job/GUI、曲線、材料、多重連結/TEM、伝搬、一般モード追跡は未対応。一般の凹多角形に対する固有場の絶対誤差や角ピーク精度は、この三角形解析だけでは保証しない。

三角形の精度ゲートは独立API計算で確認する。保存・CLIは別の回転矩形（n8×6）、凹L字（n4/16）と付属の粗い三角形例題で確認し、APIの最大分割と検証範囲を区別する。


## 主ツリーの受入証拠

標準835件（833合格、2skip、unittest1233.849秒）、独立三角形24FEM、回転/尺度16FEM＋参照4FEM、CLI・32プローブ/16replay・凹L字・規格化を確認。旧平面32件/TE10件、TM seed9モード19量と486source、36新規native hashも照合した。 command全体のtests時間は1234.238秒。最終標準/seed照合はout/validation-planar-polygon-product-final-20260909。

P1最終の最大相対誤差はf 3.821712e-05、スカラー場 7.952879e-05、派生場 0.008742856、G 0.0001287675。

P2最終の最大相対誤差はf 1.331249e-06、スカラー場 4.871828e-05、派生場 0.001632442、G 0.004053676。

独立物理はout/planar-polygon-physics-final-20260909、変換/API/CLIはout/planar-polygon-product-final-20260909、全成分probeと20native hashはout/planar-polygon-cli-probes-final-20260909、規格化/再生はout/planar-polygon-normalization-final-20260909、凹L字はout/planar-polygon-concave-final-20260909、付属例題はout/planar-polygon-examples-final-20260909、旧保存はout/planar-polygon-native-regression-final-20260909。粗いsmoke検証の非零終了を保持し、物理許容差は変更していない。

次は[平面Project・ローカルジョブ](PLANAR_JOBS_PLAN.md)。親P02全体の完了ではない。

最終照合の補助driverは生成位置の誤りによるSyntaxErrorで一度終了1となり、元driverとログを保持して修正後に終了0。製品source486・物理ゲートは変更していない。標準終了時には既存workspace/.manager.lockのResourceWarningが1件あり、資源解放の残件として保持する。
