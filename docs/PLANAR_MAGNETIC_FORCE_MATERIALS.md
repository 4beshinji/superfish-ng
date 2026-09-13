# S05: B-H・反跳材料解からの平面Maxwell応力

2026-09-13 JST。固定851sourceを主857sourceへ統合し、専用API範囲で限定受入。

`planar_magnetic_force` を実際のPlanarBHSolution（P1）とPlanarRecoilSolution（P1/P2）へ拡張した。元Caseを元ソルバーで再求解し、絶対/相対Az・基準値を確認する。元Bと[既存の平面応力積分](PLANAR_MAGNETIC_FORCE.md)を用い、元場の補正や解析係数の注入は行わない。

重みが変化する全セルはJz=0の宣言真空に限定する。B-Hでは全表点の入力floatを有理数で比較してH/B=1/MU0、反跳では宣言主値(1,1)と残留B=(0,0)を要求する。局所接線、近似的透磁率、ほぼ零の残留磁化では代用しない。対象全セルはw=1、外周はw=0、対象外の電流/非真空材料はw=0。非線形B-Hや異方性/残留磁化の対象を実FEM解へ保持する。

拡張応力報告version 2は元physicsと真空判定規約を追加する。力[N/m]、重み付きトルクと節点回転応力トルク[N m/m]、原点・重み・全セル寄与と3/4次数求積診断を保持する。線形スカラー報告version 1、線形仮想仕事と線形nativeは変更しない。今回の保存/CLIと既存 `planar_magnetic_virtual_work` は引き続き線形限定で、材料仮想仕事は次工程の別専用APIとする。

最初の独立不変量は対称mu_rec=1永久磁石の磁気モーメントトルク。元実FEMは求解済みだが旧APIが型を拒否する失敗を保存した。合成中心正方形のm/L=面積*Brem/MU0と外部一様Bから、自己力/自己トルクは対称性で零、外部トルクは(m×B)z/L。代表例の解析値は−19.4280936417 N m/mで、節点回転応力が一致する。

最初のP2細分試験は相対誤差2.1761e-14→3.3099e-14を厳密減少と比較して失敗した。この対称例のP2重み付きトルクも丸め精度で解析値と一致するため、全P2メッシュに既定の厳密対照1e-9を適用した。P1は減少と最細0.02を維持し、元場/積分コードは変更しない。修正前試験・失敗ログと判断は `out/planar-magnetic-force-materials-development-20260913` に保存した。改訂6unitは49.938秒でPASS。

独立62例は561.230436秒でPASS。線形極限B-H/反跳の電流力/偶力24例、永久磁石24例（P1/P2、8/16/32、8系列）、非線形/異方性の対称性8例、重み6例を含む。回転0/.3、尺度.5/2、電流/残留磁化反転、原点変更を別に検査した。厳密対照最大3.928e-10、原点則3.549e-13、材料零力対称性3.505e-14。P1重み付きトルクは全4系列で改善し最細最大0.000622073、P2は全メッシュ1e-9以内。全求積差1e-12以内。

旧線形56応力・40仮想仕事、旧native24報告を全JSON再計算し一致した。旧275ファイルと新186入力/結果、候補851sourceは不変。証拠は `out/planar-magnetic-force-materials-independent-trial-20260913/report.json`。標準は `out/validation-planar-magnetic-force-materials-candidate-20260913`。

[受入計画](PLANAR_MAGNETIC_FORCE_MATERIALS_PLAN.md)の応力APIのみが対象。材料仮想仕事は[次の計画](PLANAR_MAGNETIC_VIRTUAL_WORK_MATERIALS_PLAN.md)、材料保存CLI・GUI・軸対称とS05全体は未完。小さな残差/差分を連続場・力の誤差保証と扱わない。新規外部資料・依存・旧版実行なし。

標準2990.853秒、1353合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは49.935秒でPASS。標準/独立の固定851sourceと主857source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
