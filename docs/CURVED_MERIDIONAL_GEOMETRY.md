# 穴付き軸対称断面の明示二次幾何

[計画](CURVED_MERIDIONAL_GEOMETRY_PLAN.md)の固定候補646sourceを主ツリーへ統合し、以下の範囲で限定受入。
直線MeridionalMesh/AxisConnectedMeshの頂点と接続を保ち、全辺の中点を明示した二次多項式を幾何の正本とする。
円・楕円の厳密表現、解析曲線の自動生成や曲線Hφの固有解を意味しない。

`CurvedMeridionalGeometry(base_mesh, edge_vertices, edge_midpoints_rz_m, max_boxes_per_pair=10000)` は、検証済み元メッシュを再構築してから全辺を照合する。
辺の端点は小さい番号から順に並べ、辺の全リストを辞書式順序で指定する。中点の省略・頂点の変更や暗黙の辺補完は行わない。
専用schema_version 1の `to_dict/from_dict` に全入力を保持し、未知フィールド・別モデル・不正型を拒否する。

各セルで二次多項式の半径とJacobianの最小値を、binary64入力を表す厳密な有理数で求める。
正半径領域はr>0、軸接続領域はr≥0を要求し、宣言した軸の中点をそのままの直線座標に固定する。
軸以外の境界の内部にr=0があっても拒否する。既存の数値的な全セルJacobian検証も維持する。

大域検証は全辺の共有/向き、セル連結性、境界の次数2・閉路数1+穴数、Euler標数1−穴数と、全二次辺の交差を調べる。
`check_curved_edges` は明示 `hole_count` を受け取り、省略時は従来の穴なし契約と結果キーを保つ。
予算 `max_boxes_per_pair` は辺対ごとの分割上限であり、全対を合計した実行時間の上限ではない。分離が未解決なら受け付けない。

面積と半径一次モーメントは全セルの多項式から厳密に積分し、向き付き全境界の積分と厳密一致を確認する。
外周面積は正、穴は負の向きを保持する。回転体積は半径一次モーメントの2π倍。
この幾何の符号付き面積と、全PEC面に加算するRF壁損失は別の量である。

## 検証

拡張前は正常な1穴・2穴の直線極限がEuler条件で拒否された（out/curved-meridional-geometry-development-20260912/before-invariant.json）。
追加5unitは0.807秒、行列を含む関連22unitは3.306秒でPASS。
節点だけでは発見できない負半径とJacobian反転、軸変更、境界接触・辺交差、辺/型/予算違反を検査した。

独立検証は軸あり/なし・0/1/2穴・2メッシュ密度・2尺度・3変形の72幾何と72JSON往復。
合成矩形穴を既知の可逆写像 `(r,z) → (r,z+αr²)` で変形した。写像のJacobianは1でrを保つため、元矩形群の解析面積と回転体積が不変になる。
別のVandermonde再構築・二次元/境界Gauss積分で照合し、最大相対差1.111e-15、座標/勾配patch差2.532e-14。
固定646sourceで8.742秒でPASS。行列追加前の72幾何検証11.524秒も履歴として保持する。

証拠はout/curved-meridional-geometry-independent-final-20260912と同development出力。
標準回帰・本体統合・主ツリー検証も終了した。ベンチマーク/許容差は変更していない。
自作の二次要素・辺分離処理を再利用し、新規外部資料・依存・旧版参照なし。

追加の半径非線形写像 `R=r+αr², Z=z+βr²` も、固定製品ソースを変えず検証した。α=2/scale、β=−1/scaleでJacobian>0、変換後の半径に関する解析モーメントを使う。
軸あり/なし・0/1/2穴・P1/P2・2尺度の24ケース/48 RF、12CLI・40native不変が14.345秒でPASS。
最大相対差は解析形式2.177e-14、f7.128e-14、RF7.223e-15、元場L2差1.161e-15。半径重みと真の曲線境界を同時に変えた有限FEMの追加証拠である。
全3候補の不変な基盤ソースとの対応をout/curved-hphi-radial-map-independent-20260912へ記録した。実行済みhelperはout/curved-hphi-native-development-20260912/operation-helpersにhash付きで保持する。

標準1091件（1088合格・3skip）は2251.925秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。新規GUI変更はない。
主関連22unitは3.374秒、主72幾何は8.791秒、主72形式は18.460秒でPASS。
候補646sourceと主652source（不変egg-info 6件）の一致を確認した。
旧seed9モード19量はf差0、最大相対差8.882e-16。ベンチマークと数値しきい値は不変。
統合証拠はout/validation-curved-meridional-geometry-candidate-20260912/seed_regression.json。
