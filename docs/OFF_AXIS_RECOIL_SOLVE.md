# S03: 軸非接続の反跳材料の境界付きFEMと元6場

2026-09-13 JST。固定783sourceを主789sourceへ統合し、専用API範囲で限定受入。

[限定計画](OFF_AXIS_RECOIL_SOLVE_PLAN.md)に沿って、全r>0のOffAxisRecoilCaseを実装した。固定psiとHt、全Jphi、材料テンソル/残留B/向き・phiモデルを明示する。少なくとも一つの固定psiを要求し、基準値と相対/絶対係数を保持する。電流・残留・境界の三荷重で実FEMを解き、元psi/Aphi/Br/Bz/Hr/Hzを復元する。Hにはnu(B−Brem)を使う。

U/R/W0/Ws/C0[J]、Wb磁束、元H周回と固定psi反力[A]を別々に出力する。自然荷重と固定反力は+2pi∫HtNi ds、+2pi∫Ht ds。離散の仕事/電流恒等式は元場の精度を代替しない。基準Cの変更はAphiにC/rを加え、B/Hと構成ポテンシャルは不変。除かれた軸を通る絶対磁束は補わない。

初回はB=0かつH=−nu Bremが有限、非零固定psiの解析対照で、相殺する境界仕事の丸め誤差を同じ相殺後の量で正規化して拒否した。同じ問題を既存平面P2でも再現した。[仕事検査の修正](RECOIL_WORK_BALANCE.md)では各DOF積の絶対値を用いる条件付きの尺度を導入し、許容1e-9と既に受理できた結果の診断値を保つ。追加6unit・回帰2unit・既存平面6unitは13.008秒でPASS。過去平面48nativeを再構築し、全結果と元240ファイルの一致・不変性も確認した。

修正後の独立検証では一様場・向き付き界面・層状材料・電流源・B=0/有限Hと細分88例を通過した後、非零psi基準の零磁場対照で比較スクリプトが失敗した。B/Hは厳密ゼロでもAphi=C/rは非零であり、独立した半径の三項和による丸め差約5.492e-18を誤って厳密ゼロと比較していた。検証器だけを改訂し、psi誤差・B/H・構成ポテンシャル/周回/磁束の厳密ゼロを維持した。非零Aphiは32 eps |C|/r_min sqrt(volume)を丸め誤差の上限として照合する。改訂した8零場条件はPASS。元の全783sourceと出力は保持し、製品・unit・解析参照・細分許容値は変更していない。判断と全hashはout/off-axis-recoil-solve-development-20260913/zero-reference-decision.json。

最終候補は/tmp/superfish-off-axis-recoil-solve-refined-20260913。独立96例をout/off-axis-recoil-solve-independent-refined-20260913へ全再実行し、標準1251件をout/validation-off-axis-recoil-solve-candidate-20260913へ終了0。固定候補は不変。

平面の独立96例は121.372秒で再検証PASS。証拠はout/planar-recoil-work-balance-independent-20260913/report.json。この報告と過去48nativeの監査は零場参照検査改訂前のsourceであり、最終候補との差は軸非接続の独立検証スクリプト1件だけ。平面の製品/unit/解析参照/検証器はすべて完全一致する。

新規依存・この工程の追加外部資料・旧版実行なし。合成材料のみ。保存/CLI・対象版材料モデル、S03と全計画は未完。

最終独立96例は1520.282秒でPASS。一様8、向き付き界面8、P2二層8、B=0/有限H16、一定電流細分24、P1一様/二層細分24、零場8。表現可能場の最大相対差1.123318e-13、係数尺度則差1.812243e-14。P1 8/16/32、P2 4/8/16の元系列と許容値で各量の単調改善と最細精度を確認した。最終独立と標準は同じ固定783sourceへ結び付ける。

標準2600.916秒、1248合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主14unitは13.104秒でPASS。標準/独立の固定783sourceと主789source（不変egg-info 6件）は完全一致。独立例を主で全再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
