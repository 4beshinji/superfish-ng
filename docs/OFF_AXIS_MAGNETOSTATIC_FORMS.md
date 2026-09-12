# S02: 軸非接続の縮約磁束ポテンシャルと弱形式

2026-09-13 JST。固定741sourceを主747sourceへ統合し、専用API範囲で限定受入。

[限定計画](OFF_AXIS_MAGNETOSTATIC_FORMS_PLAN.md)に従い、直線r>0領域のOffAxisMagneticPartitionとoff_axis_magnetostatic_formsを実装した。mu_r/reluctivityと領域所有、穴/境界・面積/3D体積を保存し、軸接続や未対応物性を厳密に拒否する。

psi=r*Aphi[Wb]、Br=−psi_z/r、Bz=psi_r/rからK=2π∫nu/r gradNi·gradNj drdz[1/H]とf=2π∫Jphi Ni drdz[A]を導出した。エネルギーはpsiᵀKpsi/2[J]、断面源電流はsum(f)/(2π)[A]。全DOFと単一の定数核を保持する。定数psiはAphi=C/rのcurl-free成分であり、領域外の軸を貫く絶対磁束は決定しない。

求積16対20（指定4〜32に+4比較）、差5e-12以内。独立24×24 Gauss/Vandermonde積分と矩形−穴のlogを含む解析モーメントで照合した。独立72例、216多項式、72定数核/非定数正スペクトル、P2の一様Bエネルギー36例がPASS。K最大相対差2.656e-15、荷重1.759e-15、解析多項式3.810e-13、尺度/z移動8.075e-16。mu逆比例、源反転、JSON往復と順序変更も通過。

追加5unitはPASS。最初の尺度検査は、解析的に打ち消し合う荷重成分で浮動小数点残差同士を相対比較したため2成分で失敗（絶対差3.469e-18）。荷重全体の相対ノルムへ修正し、同じ1e-12閾値で通過。製品変更なし。理由と元ログはout/off-axis-magnetostatic-forms-development-20260913/zero-entry-norm-decision.json。

独立証拠はout/off-axis-magnetostatic-forms-independent-trial-20260913/report.json（試行名だが最終741sourceと一致）。標準1198件はout/validation-off-axis-magnetostatic-forms-candidate-20260913へ終了0。固定候補は不変。新規外部資料・依存・旧版実行なし。境界付き解・保存は後続工程。S02/全計画は未完。

独立72例は8.054秒でPASS。
標準2337.186秒、1195合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主5unitは1.145秒でPASS。固定741sourceと主747source（不変egg-info 6件）は完全一致。独立例は候補hashに結び付け、主ツリーで同じ全例を再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
