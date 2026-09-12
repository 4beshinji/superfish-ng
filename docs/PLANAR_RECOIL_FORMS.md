# S03: 平面の反跳透磁率テンソルと残留磁束の弱形式

2026-09-13 JST。固定754sourceを主760sourceへ統合し、弱形式API範囲で限定受入。

[限定計画](PLANAR_RECOIL_FORMS_PLAN.md)の専用LinearRecoilMaterial/OrientedMagneticRegion/PlanarRecoilPartitionとplanar_recoil_formsを実装した。正値の主軸mu_r 2成分、同じ主軸の残留B[T]2成分、各領域の向き[rad]を明示し、mu/nuテンソルと残留B/nu Bを同じ向きへ回す。全セル所有とJSONを厳密に検証し、有限性・正値性・逆行列が数値的に解決できない入力を拒否する。

K、Jz荷重、残留磁束荷重を別に組み立てる。定数Az核を保持し、残留荷重の総和は0。一様B=BremのH=0条件をKc=fremで照合する。構成ポテンシャルはB=0を零点とするw0とB=Bremを零点とするwsを区別し、その定数差をJ/mで報告する。絶対的な磁石内部エネルギーや不可逆過程は定義しない。

追加5unitは0.168秒でPASS。独立72例・216多項式・一様零H24条件もPASS。18×18 Gauss/Vandermonde積分、別式のテンソル回転、矩形−凹欠損の解析モーメントでK/fJ/fremを検証した。主軸mu倍率、材料と幾何の同時回転・平行移動、符号反転、領域順序・JSON往復を確認した。源仕事が厳密ゼロになる奇モーメントはCauchyノルム尺度を明示する。

独立証拠はout/planar-recoil-forms-independent-20260913/report.json。最初の試行も数値検査は通過したが、各ケースの行列差欄が多項式仕事の差で上書きされていたため、診断保存だけ修正して再実行した。製品とunitは不変。標準1213件はout/validation-planar-recoil-forms-candidate-20260913へ終了0。固定候補は不変。

数学の出典・独自導出は限定計画に記載。公開資料の数式のみを照合し、サンプルコード・材料表は転用していない。新規依存・旧版実行なし。境界付き解・元H/Bの界面・保存、軸対称、対象版のモデル確認とS03/全計画は未完。

独立72例は1.959秒でPASS。K差3.474320e-15、電流荷重差2.205187e-15、残留荷重差5.061144e-15、回転/尺度差4.204369e-15、零H残差1.357905e-13。
標準2409.230秒、1210合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主5unitは0.164秒でPASS。固定754sourceと主760source（不変egg-info 6件）は完全一致。独立例は候補hashに結び付け、主ツリーで全例を再実行したとは扱わない。旧ベンチマーク/許容差不変。統合証拠は標準出力内seed_regression.json。
