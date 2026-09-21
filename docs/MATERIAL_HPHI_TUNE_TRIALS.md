# 固定材料候補・最終細分・比較空間

2026-09-22。H16-aを受入。[元Project形状則](MATERIAL_HPHI_SHAPE.md)と[材料細分](MATERIAL_HPHI_REFINEMENT.md)を候補生成・追跡要求へ接続した。[目標周波数探索・ID回復](MATERIAL_HPHI_TUNING.md)も接続済み。所有保存・CLI/worker/GUIはH16-c/dへ残す。

`build_material_hphi_tune_trial(project, law, value, ...)`は専用材料Projectと形状則を受け取り、毎回元Projectからsearchまたはrefinement候補を作る。refinementは明示1〜8段の全セル4分割で、元材料・領域・界面を保持する。出力`MaterialHphiTuneTrial`には実候補Project、元Project、未細分候補partition、各細分セルのroot_cells、合成P1/P2移送、診断を保持する。

最終要素数・DOF・最低限の共通分割候補数を形状生成前に検査する。各段と未細分候補から最終partitionへの全領域/界面被覆を検証し、誤った細分を元領域と扱わない。加速区間は形状段階で移送し、細分の各Case生成でも真空軸規約を再検査する。移送係数を新固有場と扱わず、候補Caseを実FEM solveする。

`material_hphi_trial_comparison(previous, current, ...)`は同じ元Projectから生成された二つの試行だけを受け取る。未細分候補同士の明示直線写像を制御メッシュとし、各実候補からさらに一段細分した材料P2空間を有限スペクトル用に準備する。前後の実候補と制御メッシュ、両側の同領域比較空間を混同しない。

返り値は完全な`MaterialHphiTrackingRequest`で、前後の実候補間の比較と、各元側の同領域比較という三宣言、ID/集合、controls、界面/点予算を保持する。加速波形の位相、材料係数、元RF、実周波数の倍率を推測・変更しない。点数予算は射影損失の追加求積次数も含めて確認し、各下位処理でも実数を検査する。

## 条件別検証

`out/h16-material-trials-20260922/`。`before.log`でAPI未実装のred。`initial.log`は新3件22.014秒PASS。`axis-related.log`は追加1件＋関連6件、19.267秒PASS。新4件は分割実行証拠。全handle終了0。

- 正半径/穴付き軸の二段細分で全セル16倍、root材料所有、合成移送の`PᵀK_fP=K`と`PᵀM_fP=M`、元Projectと読み取り専用配列を検査。
- 予算不正を形状生成前に拒否し、異なる元Project同士の試行比較を拒否。
- 検索から実最終細分へ、別々の材料FEMをsolveして元E/Hの個別IDを確認。
- 穴付き軸の縦方向変形＋局所界面屈曲で、実最終細分・全加速座標/位相原点/beta・比較空間と個別IDを確認。点予算不足を拒否。

関連は`test_material_hphi_refinement`2件と`test_material_hphi_shape_tuning`4件。これらは全領域体積、全界面、P1/P2多項式/静的q/軸DOF、実FEM尺度則、軸移動/fold、真空加速区間/軸外原点拒否を確認する。H16-aの材料形状則・領域細分・全加速座標・元領域ごとの比較空間・予算という受入条件を満たす。

今回共有FEM core/seed TMの変更はなく、専用APIと直接利用先に検査を限定した。既存自作形状・細分・材料追跡を組み合わせ、新規外部資料・依存・legacy参照なし。全suite、目標調整成功、物理誤差上界やGUIの受入を主張しない。
