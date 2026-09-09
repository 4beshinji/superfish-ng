# TE収束Studyの仕様・受入記録

2026-09-09。独立パラメータ掃引の標準検証待機中に、既存実装から必要条件を整理した。
TE専用比較・Study/GUIへの接続を限定受入済み。以下は着手時設計と経過記録であり、最終状態は本節を優先する。

標準18688・最終照合16153は終了0。785件中783合格・2skip（unittest1181.171秒、command1181.523秒）。TM seed9モード19量の周波数差0、RF/エネルギー最大相対差8.882e-16、旧TE保存7件差0。標準・独立・GUI・固定時・終了後460対象hashが一致。out/validation-te-convergence-20260909にtests.log/command.log/validation.json/source-fixed.json/verify_completion.py/comparison.log/seed_regression.jsonを保持。

独立21FEM（円筒12・球形9）、Chrome4項目、実worker中止/完了/再起動、CLI/GUI数値一致、旧TM保存Study3件と追跡全文書一致を確認。全関連実行は終了しソース固定を解除。後続は[TE鏡映](TE_REFLECTION_PLAN.md)。

## 着手時の不適合箇所

`studies.compare_refinement` はTM専用native読込、Hφの標本内積、軸Ezの相対L2、
R/QとTTFを含むRF_KEYSを使う。TEでは軸Ezと軸電圧がゼロで、R/QはN/Aである。
この経路のTE拒否を外したり、N/Aをゼロへ変換したりしてはならない。
`fixed_geometry_convergence` の曲線元メッシュ照合もTM専用readerである。

## 実装時に確定する比較契約

- 同じ物理Caseで、異なる離散化だけを比較する。偏波混在・境界条件/正規化/物理形状の変更は拒否する。
- TE専用nativeを完全検証し、Eφを体積重み付き標本内積で対応付ける。符号の任意性を除去する。
  個別IDが不明な縮退・近接モードはUNVERIFIEDとして扱い、順位番号だけで合格させない。
- 電場Eφと磁場Hr/Hzの体積相対L2変化を別々に記録する。軸Ezのゼロを場収束合格に読み替えない。
  エネルギー規格化を保持した場を比較し、磁場quadratureの位相規約も保持する。
- 周波数と適用可能なRF量（G、Q0、壁損失、電磁エネルギー）を個別に比較する。
  軸加速量、R/Q、TTFはN/A理由を残し、合格条件の数値配列に混ぜない。
- 標本・積分次数と共通領域を記録する。粗い点標本だけの一致を場精度保証にしない。
  同一形状でもメッシュ依存の標本集合が結果へ与える影響を独立評価する。
- 幾何近似も変わる通常メッシュ細分と、元二次写像を固定した細分を区別する。
  曲線の境界再投影がある系列を固定離散幾何のFEM誤差と呼ばない。
- 細分間変化は真の誤差上界ではない。表面ピークの物理収束は別の検証範囲とする。

## 必要な証拠

1. TM専用比較へTE nativeを渡す失敗を先に記録する。円筒Besselと球形TEを用いて、
   周波数・電場・磁場・Gを独立解析と比較し、P1/P2・曲線P2の細分傾向を検査する。
2. 異なる物理Caseの拒否、符号/同一正規化の保持、縮退の未確認、粗い系列のFAILを確認する。
   合格する系列のみ選んで初期失敗を消さない。
3. Study/API/CLI/worker/GUIを接続し、保存結果/元meshの完全再検証、N/A理由と
   電場・磁場・RFの判定を画面で区別する。改変・中止・再起動も含める。
4. 旧TM Study/収束報告は書式と判定を保持する。標準数値回帰・独立解析・固定sourceを照合し、
   受入結果に応じてREADME/対応表/計画/実装状況/来歴を更新してコミットする。

新たな物理式・外部資料・依存の採用はこの設計では行っていない。

## 独立の体積場比較候補

主ツリーを変更せず、out/te-convergence-field-candidate-20260909/verify.pyを実行。94381終了0、6実FEM（P1/P2×nr12/24/48）・Gauss標本次数48/96で2モードの解析周波数・Eφ体積L2・Hr/Hz体積L2・G誤差が細分ごとに減少した。各隣接水準の場変化も別に保持。既存R35の円筒解析を再利用し、候補のreport.json/command.log/6保存結果を保持。主ツリー455source不変。
同一保存TEをcompare_refinementへ渡してもTM readerで拒否される現行不適合をred.jsonに記録した。これは候補計測であり、一般形状/曲線・縮退・Study/API/GUIへの収束接続や最終精度の合格ではない。

この系列の最細P1でも磁場の解析相対L2は約2.3〜3.8%、G誤差は約3.5〜5.1%残る。周波数誤差だけ（約0.026〜0.075%）なら良好に見えるが、場/RFの精度合格ではない。この実例を周波数・場・RFゲートを分ける受入根拠とする。P2最細では磁場L2約0.017〜0.047%、G約0.037〜0.104%だが、標本次数依存と一般形状の受入は引き続き必要である。

## 主ツリー実装中（基準9010591）

`te_convergence.py`へ専用native/hash前後照合、同一物理Case、両native分割の全セル体積積分（128セルずつ）、Duffy次数3/5照合、Eφ対応・近接縮退の未確認、電場/磁場相対L2・適用可能RF量のゲートを追加。定数2πは内積比で相殺する。軸加速量はN/Aとして判定から除く。サンプリングの次数差は物理誤差上界ではない。

既存compare_refinementは偏波で分岐し、TM本体は保持。Studyの全TE拒否を専用比較への接続に置換し、固定曲線元mesh読込もTEへ分岐。GUIはTEの電場/磁場/積分安定性を別表示し、capability/未対応文言を更新した。GUI実操作・最終独立解析・標準はまだ未実施。

追加8unitは8.917秒PASS、TE関連33件16.847秒PASS、既存TM Study11件PASS。最初のAPI5件1.953秒PASS。曲線Study追加時に写像評価へ三つの重心座標を渡して失敗し、二つの参照座標へ修正。初回失敗と修正版logはout/te-convergence-development-20260909へ保持。

out/te-convergence-study-kinds-20260909のverify.py/command.log/report.json、49713終了0。
8実FEMでmesh/明示元mesh固定細分/固定曲線/幾何近似Studyを計算し、全保存再検証と比較結果再計算が一致。前二者PASS、粗い固定曲線UNVERIFIED（積分安定性未達、磁場3.39%/G7.54%変化）、幾何近似系列FAIL（電場1.17%/磁場4.83%変化）。この検証のPASSは経路/保存一致であり、全系列の精度合格ではない。

後続受入: 円筒/球形の独立f/電磁場/G解析、細分系列のPASS/FAIL/UNVERIFIEDと積分次数依存、磁気対称/混在拒否、CLI/worker/GUIの実操作と中止・再起動、保存改変、旧TM全書式/標準回帰を検証し、文書とコミットを確定する。現時点の主ツリー変更は未コミット、全実行終了。

## 独立解析・実操作の追加進捗

円筒独立35049終了0、out/te-convergence-cylinder-independent-20260909。12新FEM、P1/P2×両尺度×3水準、Bessel f/電場・磁場体積L2/G誤差減少・Maxwell則・保存比較再計算一致。P1最終UNVERIFIED、P2最終PASSかつ解析精度条件を満たす。検証器はscripts/validate_te_convergence.py。
追加の磁気対称細分/mixed TE-TM拒否で10unit31275終了0（9.894秒）。GUI66312終了0、out/browser-te-convergence-20260909、Chrome4項目/3実Study6FEM/三判定/電場・磁場/RF/N/A理由と場取込がPASS。fixed-curved.png目視。実装hash前後一致・外部要求0。driverはscripts/verify_gui_te_convergence.mjsへ保持。GUI38411/PID1008734はSIGINT終了0。
worker86671終了0、out/te-convergence-worker-20260909、実worker中止・2点完了・管理器再起動・追跡/replayPASS。CLI84435終了0、out/te-convergence-cli-20260909、固定曲線の未確認判定を保存。
GUI独立初回20977終了1はCase JSONの0.0/0等の表記でshaが違うため全文書比較が失敗。失敗log/driverとcase-serialization.diffを保持。修正版74040終了0、out/te-convergence-gui-independent-20260909: 再起動4job verify=True、GUI/保存要約一致、全比較再計算一致、CLI/GUIの各元case hashを個別検証し、解析Case・全係数/周波数・数値/判定が完全一致。hashを同一視していない。
球形の両尺度/磁気半領域×3水準9FEMは2536実行中、out/te-curved-convergence-independent-20260909、log /tmp/te-curved-convergence-independent-20260909.log。scale1-full PASS出力済み、全完了はまだ確認していない。検証器scripts/validate_te_curved_convergence.py。最終ソースで円筒再検証26448も実行中、out/te-convergence-cylinder-final-20260909、log /tmp/te-convergence-cylinder-final-20260909.log。両実行が終わるまでsrc/tests/scripts/examplesの変更は保留。標準は未開始。

円筒最終26448は終了0。12FEM・Bessel解析・両尺度・全保存比較一致PASS、460source一致。球形2536のみ継続中。両独立完了後に標準validateと最終旧TM/TE数値比較を実行し、README/対応表/実装状況/物理・来歴を更新、commitする。

標準検証18688を開始、out/validation-te-convergence-20260909、log /tmp/validation-te-convergence-20260909.log。source-fixed.jsonの460対象を終了まで固定。球形2536も継続中。最終比較用verify_completion.pyを標準outに準備（未実行）、円筒12FEM/球形9FEM/GUI4job/旧TM Study3件/旧TE保存7件/seed9mode19量を要求する。旧TM Study再検証44586は実行中、out/te-convergence-development-20260909/old_studies.log。README/対応表/計画/実装状況・物理モデル/来歴に接続・最終検証中の範囲を追記。

球形2536終了0、out/te-curved-convergence-independent-20260909/report.json/command.log。9FEM（両尺度の全領域・磁気半領域×3水準）で最終比較PASS、解析相対誤差最大f2.508e-5/G1.999e-3/場成分3.836e-3、Maxwell相似PASS、460source一致。旧TM Study44586終了0、3保存Studyの全細分比較と旧追跡文書full replayが完全一致。標準18688のみ継続中、ソース固定。全独立・GUI・CLI・workerは終了。
