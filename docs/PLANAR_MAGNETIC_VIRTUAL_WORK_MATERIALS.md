# S05: B-H・反跳材料の平面仮想仕事

2026-09-13 JST。固定854sourceを主860sourceへ統合し、専用API範囲で限定受入。

専用 `material_planar_magnetic_virtual_work(case,body_region_ids,weights,origin_xy_m,translation_steps_m,rotation_steps_rad)` はPlanarBHCase P1/PlanarRecoilCase P1/P2だけを扱う。既存の線形用 `planar_magnetic_virtual_work` は型契約とversion 1報告を維持する。元の材料応力version 2も変更しない。

対象全セルw=1、外周w=0、他の源/非真空材料w=0、変化する全セルが厳密な宣言真空・Jz=0という[材料応力条件](PLANAR_MAGNETIC_FORCE_MATERIALS.md)を継承する。元頂点のP1重みによる±並進/剛体回転から別Caseを作り、各領域の積分電流、境界値と基準Azを保持して実FEMで求解する。反跳の対象領域はorientation_radへ実回転角を加え、透磁率主軸と残留Bを一緒に回す。解像できない節点変位や材料方向の加算を拒否する。

B-HのΠは真のH(B)表積分UからAz·(J荷重+Ht荷重)を引く。反跳ではB=0基準のU0=∫(B·nu·B/2−B·nu·Brem)dAを用い、同じJ/Ht仕事を引く。U0が既に含む残留磁化結合をremanent_load仕事として二重に引かない。H=0基準のポテンシャルと両者の材料体積定数も記録し、両基準の微分を独立に照合した。

材料報告version 2は元Case/physicsと要求、元FEM、全±変位Case、構成ポテンシャルと基準、停留ポテンシャル、J/Ht仕事、残差、相対Az SHA、B-H反復履歴を保持する。回転の差分は節点回転応力トルクと比較し、P1の重み付きトルクを同じ変位と扱わない。

元/変位先の真の非線形失敗は `PlanarMagneticVirtualWorkFailure` と保存可能なreportに保持する。status=failed、失敗した種類/刻み/符号/Caseと元のMagneticNonlinearFailure全履歴・最後の有効係数を保存する。完了済みの差分/成功側は保持し、失敗を含む対の差分はnull。暗黙の刻み縮小や失敗側の推定は行わない。入力不正と有限算術/幾何不正はValueErrorで区別する。

先行反例では、対称永久磁石の形状だけを回し磁化方向を固定すると、実差分トルクはほぼ0で解析−19.4280936417 N m/mに約100%ずれた。材料方向を共回転すると刻み.001/.0005 radで相対差1.667e-7/4.167e-8。試行Case/ポテンシャルとプロトタイプを保存した。これは元FEMの物理不変量からの検証で、解析力を製品求解へ代入していない。

追加6unitは47.933秒でPASS。Lorentz力/偶力、磁気モーメント、非線形/異方性残留磁化、方向/体積/電流とポテンシャル基準、元Case失敗、最初の変位失敗、4対完了後の回転失敗を検証した。失敗Caseの再求解で元の非線形履歴と完全一致し、途中失敗の差分をnullに保持した。

独立50条件（線形極限24、磁気モーメント8、非線形/異方性材料12、重み6）、原点変更4条件、完了54系列の648変位FEMと12実非線形失敗（途中成功分は失敗記録に別途保持）は894.153523秒でPASS。応力/実差分最大1.66671e-07、解析/実差分1.66671e-07、ポテンシャル基準変更の微分差1.09719e-10、原点則2.18378e-08は全て1e-5以内。積分電流差1.77636e-16、領域面積差3.55271e-15は1e-12以内。

材料62応力、旧線形56応力/40仮想仕事と旧native24報告を全JSON再計算して一致。元461ファイル、新166入力/結果、固定854sourceは不変。証拠は `out/planar-magnetic-virtual-work-materials-independent-trial-20260913/report.json`、標準は `out/validation-planar-magnetic-virtual-work-materials-candidate-20260913`。

[受入計画](PLANAR_MAGNETIC_VIRTUAL_WORK_MATERIALS_PLAN.md)の専用API範囲。材料保存/CLIは[次の計画](PLANAR_MAGNETIC_FORCE_MATERIAL_NATIVE_PLAN.md)、GUI・軸対称と親S05・全計画は未完。小さい差分/残差を連続場や力の誤差上界と扱わない。既存の公開変分・B-H/反跳構成則から自前に導出し、新規外部資料・依存・旧版実行なし。

求解数の数え方：独立報告のsuccessful_displaced_fem_solves=648は完了した54系列の値。12失敗例には、失敗前に成功した32変位FEMが別途trialsとして残る。成功変位の総数は680だが、失敗系列の完了扱いにはしない。開発証拠work-count-interpretation.jsonに区別を保持した。

標準2987.789秒、1359合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは48.657秒でPASS。標準/独立の固定854sourceと主860source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
