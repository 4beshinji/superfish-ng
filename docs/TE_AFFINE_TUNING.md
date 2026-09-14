# TEアフィン曲線変形と調整版4

2026-09-15、開始HEAD `c65d58e`。曲線TEの版4接続を進める。
受入条件はEφの写像、全二次境界一致、独立体積比、一様寸法のMaxwell周波数則、
native保存再開、N/A加速量、既存TM互換である。実GUIを含む追加受入は別途必要。

宣言写像は r_new=a r_old, z_new=b r_old+c z_old、a,c>0。
体積比a²cは一定で、二つの実曲線メッシュ上の積分を旧領域へ引き戻す。
TEでは実Eφを評価し、現在側を1/a倍する。この定数は列の正規化で消える。
方位角を変えない子午面写像に対応するスカラー方位成分の比較である。
全二次境界一致とnative曲線の対応するパラメーター、正の体積重みを従来どおり検査する。
異なる偏波、非曲線TE、TE鏡映を拒否する。閉PEC/軸境界の直接P2が対象。
同じ曲線領域のcurved_same_domainもTE専用readerとEφ比較へ接続する。

TEのrf_coordinatesはfixedのみ。変形で加速区間・加速長・位相原点を新設しない。
既存TMの固定/軸長連動と、省略した位相原点の扱いは維持する。
版4の各試行間には相対アフィン写像を導出し、最終細分は同じ二次領域を制限する。
TE affine Studyの独立した旧制限は変更していない。

試験場Eφ=rは正則な多項式アダプターであり、PEC固有モードとは呼ばない。
せん断検査には軸上の両端と中間の正半径頂点を持つ合成円錐形状を使用し、
重なり1と体積比a²cを確認する。楕円端部をせん断してz範囲を外す形状は拒否を維持する。
試験入力で欠けていた正の曲線線形化許容値を補い、当該1件1.917秒PASS。
同テストでTE curved_same_domainのnative保存再生も確認した。

既存関連35件134.814秒PASS：curved_project_transform、curved_same_domain_tracking、
curved_affine_remesh_tracking、affine_remesh_tracking、curved_tuning、te_tuning、TEJobの未接続workflow拒否。
TEJobのアフィン拒否テストは未対応のaxial RF方針を明示的に検査する。
全suite/seed/実GUIは再実行せず、hosted CIを観測していない。
証拠はignored out/te-affine-tuning-20260915。外部資料・依存・旧実装資産は追加していない。

TE一様尺度tuneの初期細分level1は最終周波数条件を満たさずREFINEMENT_FAILED。
許容差5e4Hzを維持して初期level3へ増し、周波数×尺度の相対差1e-10以下、TUNED、
先行保存保持・再生・全試行N/Aを確認した。初期失敗ログはnew-tests.log（25.244秒）。
増細分後のrefined-tests.logは2件501.345秒、tuneは成功、修正前の合成形状入力が1error。
同入力のcurve_chord_tolerance_mを補い、shear-fixed.logの1件1.917秒が成功。
新規2件は分割成功であり、単一実行の全件PASSとは記録しない。物理許容差の緩和なし。
全検証handleは終了。実GUI・追加場/RF尺度とTE affine Studyは引き続き必要。
このAPI実装コミットをD02全体の受入完了とはしない。
