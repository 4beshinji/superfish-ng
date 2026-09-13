# S05: 軸を含まない軸対称磁場の軸方向力

2026-09-13 JST。固定860sourceを主866sourceへ統合し、専用API範囲で限定受入。

専用 `off_axis_magnetic_force(solution,body_region_ids,weights)` はr>0・直線・線形スカラーOffAxisMagnetostaticSolution P1/P2を実FEM再求解して、基準ψ/絶対ψ/相対ψを確認する。対象全セルw=1、外周/穴境界w=0、対象外の電流/非真空材料w=0、変化する全セルmu_r=1/Jphi=0を要求する。元Br/Bzを平滑化せず使う。

真空T=(B⊗B−|B|²I/2)/MU0からFz=−∫2πr*(Tzr*dw/dr+Tzz*dw/dz)dr dz[N]を計算する。対象は断面の全周回転体。平面のN/mではない。軸対称性で全体の横方向力と軸まわりトルクは零であり、半径方向の応力を全体の横方向ベクトル力と表示しない。報告version 1にはFz、全セル寄与、元Caseとψ係数のSHA、対象/重み/真空遷移セル、元Caseの求積次数qとq+4比較を保持する。

別専用 `off_axis_magnetic_virtual_work(case,body_region_ids,weights,translation_steps_m)` は2..8個の正で厳密減少する刻みを使う。全周対象を同じP1節点重みで±z並進し、r座標と外部境界、対象外源/材料を固定する。各領域の∫Jphi dr dz[A]を保持した別Caseを実FEMで求解し、Π=U−ψ·(J荷重+Ht荷重)[J]の−dΠ/dz[N]を求める。全変位Case、Π/U/源仕事と残差・相対ψ SHAを保存する。解像できない変位、反転したメッシュ、不正重みと別physicsを拒否する。断面の回転を三次元剛体回転と扱うAPIは設けない。

独立解析対照はz対称の有限環状電流と外部Br=C/r、Bz=0、ψext=−Cz。上下固定ψと内外径Ht=0から実FEMで求解する。自己軸力は鏡映対称性で相殺し、外部力はFz=−2πC∫Jphi dr dz。I=10A、C=.0625 T mでは−3.926990816987 N。解析場の係数や力を製品解へ代入しない。最初のAPI未実装失敗と、先行の独立設計試作を保存した。

最初の独立P2/q4/n8は、元FEMの1/r行列求積差2.2822e-11が既存5e-12条件を超えて拒否された。n16では7.0583e-13となり求解と力1e-9を満たした。全q=4/8/16/32比較を同じn16へ変更し、n8/16/32のメッシュ系列とは分離した。元FEM・応力/仮想仕事式と許容差は不変。最初の部分出力はout/off-axis-magnetic-force-independent-trial-20260913、改訂前試験/validator、診断と判断はout/off-axis-magnetic-force-development-20260913に保持する。追加6unitは44.899秒でPASS、n8拒否/n16成功を追加した1試験は9.538秒でPASS。

改訂独立50例（解析42/線形磁性体8）は191.204660秒でPASS。P1/P2、尺度.5/2、I±10AとC反転、z移動、対象mu_r=3/7、n8/16/32メッシュ6例、重み6例、求積8例、基準ψ6例を確認した。解析力最大差3.92227e-10は1e-9以内。30条件/120変位FEMと応力差7.99811e-09は1e-5以内。求積差1.84491e-16は1e-10以内、積分電流/全周体積差は0/7.77156e-16で1e-12以内。

130入力/結果と候補860sourceが不変。独立報告はout/off-axis-magnetic-force-independent-refined-trial-20260913/report.json、標準はout/validation-off-axis-magnetic-force-candidate-20260913。

[受入計画](OFF_AXIS_MAGNETIC_FORCE_PLAN.md)の専用API範囲。次の[保存・CLI](OFF_AXIS_MAGNETIC_FORCE_NATIVE_PLAN.md)、軸接続/B-H/反跳の軸力、GUIとS05/全計画は未完。小さい差分や残差を連続場の力精度保証と扱わない。既存の公開Maxwell式と自作ψ弱形式から導出し、新規依存・外部資料・旧版実行なし。

標準3225.206秒、1371合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは48.204秒でPASS。標準/独立の固定860sourceと主866source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
