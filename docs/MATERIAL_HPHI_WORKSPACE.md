# 材料HφのProject・表示・独立掃引

2026-09-13 JST。[計画](MATERIAL_HPHI_WORKSPACE_PLAN.md)の固定候補674sourceを主680sourceへ統合し、本書の操作範囲で限定受入。
専用材料Caseを共通Hφ Project、所有worker・取込・取消・保存復元、独立Studyへ接続した。
材料Case/Project JSONをGUIで読み込み、全材料分割を保持して計算できる。
材料一覧・領域エネルギー・隣接PEC壁損失、非磁性壁と真空軸区間の規約を表示する。

実装前、共通Projectが材料Caseを拒否し、表示処理がBをmu0 Hで上書きすることを確認した。
検証例のB相対差は0.826806、修正後は0。元セルのmu_rを保持し、境界で平均化しない。
材料CSVはr/z・E/H/Bの18成分に、片側セル番号・領域ID・材料ID・epsilon_r・mu_rを追加する。
付随JSONにも各点の重心座標、所有情報、材料係数、片側選択規約を保持する。
真空ケースのCSV列・PNG出力は保持する。

Studyは全幾何の一様尺度、総U、壁導電率に限定する。材料係数と全セル割当は変えない。
尺度変換では全輪郭/穴/節点と明示軸区間/位相原点を変換する。順位は追跡IDではない。
材料の場比較・収束診断・追跡は入口で拒否し、GUIの真空追跡候補にも含めない。
材料係数の掃引と専用GUI編集は対象外。完全なProject JSONによる材料入力は保存再検証する。

追加5unitは元Bの不変量、材料/界面保持、U・導電率・尺度則、実worker/取込/取消/再起動、
改変Projectの拒否、GUIのStudy点復元と25列CSV/材料メタデータを確認し、18.163秒でPASS。
旧nativeテストの「Project/GUI/Studyは未対応」という旧段階だけのassertを外し、新しい実Project/Study検証へ移した。
物理しきい値は変更していない。

独立12ケース（正半径/軸・穴0/1/2・P1/P2）は12Project worker、12Study worker/24FEM、24取込、12再起動を含む。
描画三角形の領域別面積と半径モーメントを、層区間で切り詰めた解析長方形から全穴を引いた値と照合した。
最大差2.221e-16、空間尺度則5.152e-14。元native300ファイルとProject12ファイルは不変。
CLI/GUI、元ディレクトリ移動後の所有コピーでPNG・CSV・付随情報が一致し、203.128秒でPASS。

実Chromeは材料20項目、旧同軸/一般断面8項目、旧TM/TE/平面5項目、再起動復元8項目がPASS。
材料を含む軸区間の指定はジョブ作成前に拒否した。原本2ディレクトリを移動し、所有コピーから画面/Studyを復元した。
保存物65ファイルの不変、14保存ジョブの再構築、旧真空PNG/CSVの変更前一致もPASS。

標準1127件は`out/validation-material-hphi-workspace-candidate-20260913`へ終了0。主ツリー統合・5unit/12例24StudyFEM/14保存ジョブ6CLIもPASS。
証拠は`out/material-hphi-workspace-development-20260913`、`out/material-hphi-workspace-independent-20260913`、各browser出力。
材料比較/追跡、損失/分散、旧版照合、P04/O02と全計画は未完。新規依存・外部資料・旧版実行なし。

標準は2234.459秒、1124合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。
主5unitは18.256秒、主独立照合は214.056秒、主保存物照合は10.641秒。
候補674sourceと不変egg-info 6件を加えた主680sourceを照合。既存周波数/RFしきい値とベンチマークは不変。
統合証拠は標準出力内seed_regression.json。
