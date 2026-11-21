# 固定材料領域と全界面の比較分割

2026-09-22、H15-a受入。[H14契約](MATERIAL_HPHI_TRACKING.md)の領域・界面の部分を実装する。材料E/HのGram、scalar射影、有限スペクトル、ID追跡はH15-b/cで未実装。

## 宣言と保持する情報

`MaterialHphiComparison`は完全なprevious/current `RFMaterialPartition`、`mapping`、`material_pairs`、`region_pairs`を所有する。JSONは`format: superfish_ng_material_hphi_comparison`、`schema_version: 1`。mappingは文字列`same_domain`か既存の完全な`HphiGeometryMapping`版1。各pairは`previous_id`/`current_id`を持つJSON配列で、全IDの全単射を要求する。ID改名や列挙順変更は明示pairでのみ許可する。

元partitionを深く再構築し、各材料のepsilon_r/mu_rの厳密一致、領域が参照する材料対応、軸接続/正半径の型を検証する。係数変化を許容差で吸収しない。未知キー、bool版番号、暗黙対応、未割当材料/領域、曲線・損失など既存partitionが受け付けない物理は拒否する。

`material_hphi_overlay`は次を返す。

| 情報 | 内容 |
|---|---|
| `comparison` | 再検証済みの完全宣言。元セルから材料ID・領域ID・係数を取得可能 |
| `overlay` | 元セル番号、各側の重心座標、共通三角形/面積Jacobian。明示写像では制御セル、前側の元座標/面積も保持 |
| `previous_region_indices` / `current_region_indices` | 各正面積共通セルの元領域番号。ID対応を検証した結果であり番号をIDと見なさない |
| `interfaces` | 前後の元界面辺番号、各辺の両側元セル、制御セル、前後の対応する部分線分の端点。same_domainの制御セル番号は−1。currentの両側セルはprevious側の領域順に揃える |

配列は読み取り専用。元mesh/材料/領域を変更せず、固有解や場を合成しない。界面がない一様partitionには空のinterface配列を返し、架空の界面を追加しない。

## 全領域・全界面の検証

体積の共通分割には既存の有理数による直線overlayを使用する。両元FEMと制御メッシュの全被覆、正Jacobian、軸・全PEC穴の一致を検証したうえで、全ての正面積共通セルの領域pairを検証する。微小な不一致を切り捨てず、1 ULPの界面ずれも拒否する。同係数の異なる領域も併合しない。

界面は別に完全検証する。前側の各辺を制御三角形の半平面で正確に切り、区分アフィン写像で現在側へ移す。制御辺上にある線分の二重所有は同じ有理区間/像の一致を条件に一度だけ数える。現在側の元界面辺と正長の共通区間を作り、各側の全元辺についてパラメータ区間[0,1]を隙間・重複なく覆うことを確認する。端点接触だけを正長の対応としない。対応する両側領域と両側元セルを保持し、片側場の評価で界面平均を使う必要を生じさせない。

これらの被覆判定はbinary64入力を表す有理数で行い、返却データだけをfloatへ変換する。非有限値と端点のfloat上での潰れは拒否する。

予算は体積探索`max_candidate_tests`（既定2,000,000）、体積三角形`max_overlay_triangles`（250,000）、界面探索`max_interface_tests`（2,000,000）、界面分割`max_interface_pieces`（250,000）。体積と界面は別予算で、界面では制御三角形との検査と現在側の辺との検査を合算する。超過時は部分結果を返さず、求積点や界面を省略しない。

## 独立検査と来歴

出力は`out/h15-material-comparison-20260922/`。新API未実装のredを`before.log`で確認した。対象は新`test_material_hphi_comparison`と、再利用する`test_rf_materials test_hphi_geometry_mapping test_meridional_overlap`。

- 矩形から穴を引いた独立積分で、領域別面積、回転体体積π(r1²−r0²)Δz、界面長を照合。正半径/軸、穴0/1/2、独立再メッシュと反対対角線を含む。
- 非一様写像と逆写像で両側界面セルを保持。半径2倍、下層z方向2倍/上層1倍の写像で、領域面積4/2倍、体積8/4倍を確認。正半径と穴付き軸を検査。
- 制御セルを横切って折れ曲がる界面で、両側全界面長と分割を確認。
- セル/節点番号、材料/領域列挙順、明示ID改名に依存しない対応を確認。
- 1 ULPの界面位置ずれ、等係数でも誤った領域、係数変更、pair欠落/誤対応、非JSON配列、予算超過を拒否。
- 元宣言の保持、呼出側辞書変更からの独立性、一様材料での空界面を確認。

`expanded.log`は新6件＋関連10件、8.765秒PASS/終了0。厳密JSON配列と一様領域検査を追加した後、`final.log`で新7件6.094秒PASS/終了0。非一様写像を穴付き軸と領域別尺度則へ拡張し、変更した1件を`mapped-measures.log`で1.832秒PASS/終了0。全handle終端。未変更の関連検査は再実行していない。

既存自作の正確な直線分割と材料partitionを利用し、界面区間の半平面clip/全区間被覆を追加した。新規外部資料・依存・legacy参照なし。FEM組立/固有解/元RF/seed TMを変更しておらず、この幾何比較の独立積分と直接利用先の検査に限定した。全suiteや材料ID追跡の受入を主張しない。
