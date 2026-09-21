# 固定二次領域の曲線Hφ三水準診断（H12-b、受入済み）

`CurvedHphiConvergence`と`compare_curved_hphi_convergence`は、完全な一つの二次参照領域に属する3水準以上の元native場を比較する。周波数、直接E/H場差、RF、共通参照境界の各線分/各成分損失、明示軸電圧を独立に判定する。解析曲線への幾何収束や連続問題の誤差上界を判定しない。

## 要求と固定する量

要求形式は`superfish_ng_curved_hphi_convergence, convergence_version=1`。全HphiProject、完全`reference_geometry`、各水準の`native_cells`、対象`mode_ranks`、比較予算、求積次数、既存`HphiConvergenceThresholds`を明示する。native chartは[H11](CURVED_HPHI_COMPARISON.md)の厳密制限で、同じ頂点だけの照合や境界への再投影を許さない。

各水準の真空曲線Case、P1/P2次数、元FEM求積次数、正スペクトル数、蓄積エネルギー、導電率、軸加速経路を固定する。要素数が増え、全二次Bernstein制御点を包む最大boxの対角長が減少することを求める。このboxは細分の指標であり、物理誤差推定ではない。未知キー・bool順位・不正version・同じmeshの繰返し・物理量や二次領域の変更を拒否する。

## 判定と境界積分

各元FEMの正スペクトルと全native spaceを再検証し、[H12-a](CURVED_HPHI_FIELDS.md)でE/Hを別々に比較する。同順位の個別対応には、両側の上下近傍間隔、近傍周波数の水準間変動、E/H双方の内積と他候補への余裕、共通係数位相を要求する。上側guardが計算されていない順位や近縮退はUNVERIFIED。永続IDは付与しない。

場差はGramの差し引きで求めず、共通点の元場差を直接積分する。単一位相をE/Hと軸電圧に共通適用し、細かい側の場ノルムで規格化する。二次数の求積差も別に検査する。

細分でnative境界線分数が変わっても、各native境界辺のchartから元の参照境界線分へ積分を集約する。全PECの実二次弧長・半径・元Hφを使い、軸の損失は0。各参照成分の和が元RFの外周/各穴の積分と一致しなければ拒否する。名前だけ対応させたり、細分された線分を省略したりしない。

最後の二つの水準差について、対応確認、非増加、指定閾値を指標ごとに判定する。両R/Q定義と複素軸電圧を保持し、経路のない正半径領域では未定義のRF量を数値0へ変換しない。surface peak精度はnot_checked、mode_trackingはnot_performed。

## 検証経過

出力は`out/h12-convergence-20260921`。変更前は専用要求API不在で終了1（`before.log`）。最初の解析TEM対照は2/4/8分割で、RF差が閾値内でも周波数差0.000229997と電場差0.0216072が既定閾値を満たさずUNVERIFIEDとなった。検査が誤ってPASSを要求して失敗した履歴を`analytic.log`に保持する。既定許容差は変えず、4/8/16分割へ進めた対照を実行中。

初期3検査は保存native/位相、strict要求、軸接続三水準/guard。穴付き保存場の検査でエラーを記録し、最終tracebackを確認中。H12-b/親H12は未受入。

新規資料・依存・legacy参照はない。既存Bessel根・TEM場・壁積分式から独立対照を構成する。seed TM・元solver・許容差を変更していない。

初期3件は275.717秒で終了1。strict要求と軸三水準/guardの2件はPASS、保存検査は最後の改変対照でテストが幾何の`mappingproxy`をdeepcopyしようとして失敗した。保存再生/元hash/符号対照はその前に通過しているが、検査全体の成功とは数えない。係数だけを`replace`で複製するよう補修し、保存検査1件を再実行中（`saved-fixed.log`）。

解析対照の4/8/16分割は114.608秒PASS、終了0（`analytic-refined.log`）。既定閾値を維持して三水準PASSとなり、最細fを`c/(2L)`の相対3e-4以内、q場の`cos(pi*z/L)`との質量overlapを0.999超、Qを解析壁積分から求めた値の相対0.001以内と別々に検査した。同じ検査で独立Bessel根とTEMの交差長をdyadic座標へ丸めた近縮退対照を用い、既定0.001の分離条件を満たさずUNVERIFIEDとなることを確認した。丸めた形状を厳密縮退と呼ばない。

関連`test_curved_hphi_saved test_curved_hphi_field_overlap test_hphi_convergence test_curved_hphi_comparison`の19件は78.140秒PASS。P1軸場の共通符号と複素電圧保持は追加検証中。実行は既存`.venv`を`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules/cases>`で使用する。

修正後の穴付き保存場検査1件は97.372秒PASS、終了0。関連19件のhandleも終了0。失敗を隠すための物理許容差・製品FEM変更は行っていない。

## 親H12の条件別照合

| 元の受入条件 | 証拠 |
|---|---|
| 元E/H・実二次写像と体積 | H12-aのnative再構築、H11の全被覆、両3D測度と元K/M Gram再現 |
| 真空q/uと静的零空間・guardの区別 | 両定式化の正スペクトル再検証と零空間数、H12-bの未計算上側guard・近縮退停止 |
| 独立既知場積分 | H12-aのE=(0,1), Hφ=r、矩形の∫2πr/∫2πr³と非一様密度倍率 |
| 二尺度の実FEM | H12-aのf倍率1/2、両E/Hエネルギー、個別内積と元係数保持 |
| 直線極限 | H12-aの独立直線Hφ Gram、H12-bの解析TEM f/q場/Qの別照合 |
| 三水準f/場/RFを別判定 | H12-bの実曲線軸場・穴付き保存nativeと、解析TEMの粗いUNVERIFIED/細かいPASS対照 |
| 解析曲線と二次近似を混ぜない | 同じ完全P2参照領域の厳密native制限のみ許可、幾何変更拒否。解析TEMは直線極限に限る |
| 小残差を物理精度に読み替えない | 実場差・全境界損失・RF・三水準非増加を別判定し、残差からの精度保証を返さない |

P1軸位相の最終検査中。曲線の履歴/調整/CLI/worker/GUI接続は次のH13であり、H12の数値診断をその受入証拠には使わない。

P1軸場の共通位相検査は88.621秒PASS、終了0（`p1-axis-phase.log`）。E/Hと複素軸電圧の差が符号反転で不変。新5件は2件の初期成功＋保存修正1＋解析1＋P1位相1の分割証拠で、初期失敗ログも保持する。全handle終端。関連19件の成功証拠と合わせH12-b/親H12を受入。全suite/seed TM/Hosted CI/GUIの検証は本変更の証拠には含めない。次はH13。
