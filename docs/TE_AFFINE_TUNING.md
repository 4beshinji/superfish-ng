# TEアフィン曲線変形と調整版4

2026-09-15 JST：[TEアフィン調整版4](TE_AFFINE_TUNING.md)のGUI/CLI・場/RF追加検証を限定受入。
アフィン係数の重複JSONキーを元テキストのままサーバーへ渡し、FEM前に拒否する修正も実施。
Chrome TE12/TM10項目、GUI関連5件PASS。専用比較21実FEM＋解像度/目標pilot3実FEM。
7組native全配列/RF一致、元108ファイル保持。TE affine Study・版8・曲線対称/鏡映・他物理/D03等は残り、全goal ACTIVE。

追加受入（開始HEADf4d8c37）：直接閉PEC曲線P2・fixed RFのアフィン調整を実GUI/CLIまで検証。
以下の「実GUI未実施」は前段階の履歴。TE affine Study、曲線対称/鏡映などは残件として保持する。

前回のlevel3実検証を再実行せず、level2と3のTE固有値を追加2FEMで測定した。
1.1倍寸法での差22630.804Hzが既存5e4Hz条件内であるため追加受入にはlevel2を採用。
許容差は維持する。TM GUI目標のpilot1FEMを別に実行。
原寸・倍寸・4倍エネルギー各4試行=12実FEM、CLI再開1、GUI TE4/TM4、比較21FEM＋pilot3FEM。

全試行の同一パラメーター値とMaxwell尺度則を確認。周波数・G・Q0・電気/磁気/全エネルギー、
表面抵抗・壁損失・PEC接線磁場二乗積分を個別検査し、最大RF尺度差4.4409e-15。
全要素重心のEφ/Hr/Hz差6.2602e-14、全v係数差1.3464e-14、電磁エネルギー等分差2.2205e-15。
これは離散化誤差上界や表面ピーク精度の証明ではない。

GUI検証の追加で、旧アフィンフォームのJSON.parseが重複キーを失うことを見つけた。
元JSONを保持して厳密server parserへ渡し、重複をFEM前に拒否するよう修正。
検証側にも空欄解析・フォーム反映待機の不足があり、修正して先行失敗ログを保存した。
最終Chrome TE12項目/TM10項目PASS、元要求完全一致、重複拒否、固定/軸長連動RF方針復元、保存再開と最終場取り込みを確認。
製品336SHA固定・外部通信0。両画面を目視し、最終粗細差TE22630.804Hz/TM14962.132Hzが宣言条件内と確認。
直接/CLI/GUI/取り込みの7組で全native配列・全RF一致、元108ファイル保持。
全6GUI Job完了後に専用サーバー停止。最終実行は全て終了0。

GUI関連5件19.657秒PASS、JavaScript構文検査PASS。前回の数値テストは挙動変更のない実装核について再利用。
full suite/seed/hosted CIを新規実行していない。証拠はout/te-affine-tuning-acceptance-20260915。
共有要約はbenchmarks/tuning/te-affine-tuning-acceptance-20260915.json。


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
