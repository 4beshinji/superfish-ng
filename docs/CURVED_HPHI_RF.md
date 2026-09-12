# 明示曲線Hφの固有解・場・RF

[計画](CURVED_HPHI_RF_PLAN.md)の固定候補650sourceを主ツリーへ統合し、以下の範囲で限定受入。
専用 `CurvedHphiCase` に、検証済み二次幾何、P1/P2、積分次数、モード数、全3D蓄積エネルギー、導電率と任意の明示軸経路を保存する。
真空・閉PEC・m=0 Hφのみを受け付ける。正半径qでは定数静的循環を検証して除き、軸接続uでは全軸DOFと最低正スペクトルを保持する。

`solve_curved_hphi` は元K/Mから固有解を求め、全エネルギー規格化、直交性、元FEM残差を検査する。
`restore_curved_hphi(case, coefficients, frequencies)` は幾何とK/Mを再構築し、最低正帯域も再検証する。
幾何の座標範囲は節点最大値で代用せず、各二次多項式の厳密な最小/最大から導く。

`fields_in_cells` は明示した元セル/参照点の物理微分を返す。
`fields_at` は二次写像を逆に解き、穴・領域外・未解決を拒否する。共有境界では最小番号の受理された元セルの片側微分を使い、平滑化しない。
真空軸は宣言済み直線区間から直接逆変換し、Hφ=Er=0と有限なEzを保つ。
保存規約に向けた場成分はpeak exp(+iωt)、Hφ real、Er/Ez quadrature、field=real+i*quadrature。

`curved_hphi_quantities` は元場の全体積の電磁エネルギー、実曲線の弧長を用いる全PEC区間/成分の壁積分、P・Rs・Q0・Gを求める。
穴の損失は加算し、軸の面積/壁損失はゼロとする。
指定積分次数+4/+8で電磁エネルギー・全区間壁積分・表面積を別々に照合し、相対差5e-10を超えると未解決として拒否する。
明示した真空軸区間・beta・位相原点にだけ複素Vaccと両R/Qを返し、経路なしではN/Aを保持する。
二つのR/Qはそれぞれabs(Vacc)²/(ωU)とabs(Vacc)²/(2ωU)。壁ピーク値は本工程の対象外。

## 検証

初回4unitは軸上プローブでHφ=3.481e-15 A/mとなる不具合を検出した（5.096秒）。
Newton逆写像の丸めによる軸からのずれが原因だった。検証済み直線軸のz区間から参照座標を直接求める処理へ変更し、ゼロ条件の許容差を緩めず修正後4unitが5.221秒でPASS。
直線極限の既存f/全場/全壁RF・R/Q、曲線内部プローブ/導体拒否、元FEM再構築、尺度/U/導電率/軸位相原点の則を確認した。
関連26unitは11.146秒でPASS。

独立検証は軸あり/なし・0/1/2穴・P1/P2・2曲線変形・2尺度の48 FEM、144モードの元E/H・RF、48Case JSON往復と元96保存ファイルの不変。
別に構成した全K/Mの最低固有値と、Vandermonde・逆Jacobian成分式・高次Gauss積分による場/体積/壁/軸電圧を照合した。
24.190秒でPASS。最大相対差は周波数7.861e-14、RF1.022e-14、元EのL2差1.157e-15、元HのL2差3.275e-16。
証拠はout/curved-hphi-rf-independent-20260912とout/curved-hphi-rf-development-20260912。

二次多項式が幾何の正本で、合成変形を使った有限FEMの検証である。解析曲線の近似誤差・連続問題の誤差上界・曲線表面ピーク精度は保証しない。
標準回帰・本体統合・主ツリー検証も終了した。native/CLI/Project/Job/GUI/Study/追跡は別工程。
自作の固有値処理・二次逆写像・軸電圧積分を再利用し、新規外部資料・依存・旧版参照なし。

追加の半径非線形写像 `R=r+αr², Z=z+βr²` も、固定製品ソースを変えず検証した。α=2/scale、β=−1/scaleでJacobian>0、変換後の半径に関する解析モーメントを使う。
軸あり/なし・0/1/2穴・P1/P2・2尺度の24ケース/48 RF、12CLI・40native不変が14.345秒でPASS。
最大相対差は解析形式2.177e-14、f7.128e-14、RF7.223e-15、元場L2差1.161e-15。半径重みと真の曲線境界を同時に変えた有限FEMの追加証拠である。
全3候補の不変な基盤ソースとの対応をout/curved-hphi-radial-map-independent-20260912へ記録した。実行済みhelperはout/curved-hphi-native-development-20260912/operation-helpersにhash付きで保持する。

標準1095件（1092合格・3skip）は2230.517秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。新規GUI変更はない。
主4unitは5.300秒、主48 FEM/144 RFは19.225秒でPASS。
候補650sourceと主656source（不変egg-info 6件）の一致を確認した。
旧seed9モード19量はf差0、最大相対差8.882e-16。ベンチマークと数値しきい値は不変。
統合証拠はout/validation-curved-hphi-rf-candidate-20260912/seed_regression.json。
