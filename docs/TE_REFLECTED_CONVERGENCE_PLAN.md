# TE鏡映部分スペクトルの収束比較：後続契約

## 最終受入 — 2026-09-09

基準7fcf4a7。標準47383・最終数値照合27419は終了0。795件中793合格/2skip（unittest1230.296秒、command1230.670秒）。TM seed9モード19量の周波数差0、RF/エネルギー最大相対差8.882e-16。旧通常TE保存7件＋鏡映TE保存3件のRF差0。標準・最終独立・GUI保存照合・固定時/終了後467sourceとChromeの配信実装hashが一致。証拠はout/validation-te-reflected-convergence-20260909のtests.log/validation.json/command.log/source-fixed.json/verify_completion.py/comparison.log/seed_regression.json。

追加5unit/TE全52件、独立12FEM、4種Study8FEM、Chrome7操作/3Study6FEM、CLI固定曲面2FEM・GUI文書/全係数/元hash一致、再起動5ジョブと各Studyの再比較、実worker中止/完了/再起動が合格。初回GUI列名誤置換を修正し、初回失敗は保持した。旧TM/通常TEの保存Study6件とTM追跡再生が完全一致。初回ブラウザーの追加Studyも2点のnativeを再検証・再比較（initial-study-reverified.json）。

電場/磁場/RFゲート・許容差は従来のまま。数値FAIL/UNVERIFIEDをPASSへ変更せず、物理誤差上界や表面ピーク精度を保証しない。元物理/対称条件の不一致・通常/鏡映混在・比較中source_fields変更を拒否する。新規外部資料・依存・legacy参照なし。

次は[対称面付きTE円筒の追跡](TE_SECTOR_TRACKING_PLAN.md)。一時コピーのP1/P2/相似則/縮退/保存候補は製品受入には含めない。親8受入/9進行中/15他/1候補=33の集計と全計画の継続を維持する。以下は実装経過で、当時の実行中・未接続という記述より本節を優先する。

2026-09-09。基準7fcf4a7の鏡映受入後、同じ元半領域での収束比較を主ツリーへ接続し、以下の範囲で限定受入を完了。以下の初期拒否/候補という記録より最新進捗を優先する。

## 受入条件

同じ物理の元半領域・同じ対称面/対称条件に由来する二つの部分スペクトルだけを比較する。通常の全スペクトルと鏡映結果、異なる対称条件を混ぜない。native版4の元Case/mesh/係数と再構成場を全て再検証する。元半領域の番号と全領域順位を混同しない。

物理的には反射で全体積の内積とエネルギー/壁損失が2倍になるため、相対電場/磁場誤差、正規化重なり、周波数/RF相対変化は元半領域と一致する。縮退/積分未確認、電場/磁場/RFの個別判定、N/A、表面精度未保証を維持する。保存比較・CLI・Study・GUIの説明に比較した領域と部分スペクトルを明記する。

## 最初の独立反例

`out/te-reflected-convergence-contract-20260909/verify.py` はP2円筒の二つの実FEMを解き、元半領域と鏡映全領域の両分割Duffy積分を直接比較した。最初の条件で内積2倍の1e-10不変量が不合格。電場ノルムの相対差は約4e-9、磁場は約2.203e-7。これは固有値や鏡映係数の不合格とは別で、交差する分割を標本積分する比較器の問題を示す。ログ `/tmp/te-reflected-convergence-contract-20260909.log` と出力を保持。

検証器だけで三角形の全6頂点置換に積分則を対称化した `out/te-reflected-convergence-symmetric-contract-20260909` も、磁場ノルムで約7.814e-7の差が残り不合格。電場は一致した。要素境界上の磁場の片側選択が反射で一致しない可能性があるが、原因の完全な切分けは未完。許容差は緩和していない。主ツリーの製品比較器を変更していない。どちらの検査も最初の条件で停止しており、予定した8FEM全体を実行済みとはしない。

## 次の実装判断

版4で保存した元半領域を再構成し、同一物理/同一対称条件を検査してから、元半領域上の既存TE比較を使う方式を優先する。全領域への厳密反射関係とRFの2倍則を別途照合し、比較した領域と正規化を出力へ記録する。全領域の任意標本点における片側磁場の値を、独立の物理誤差証明としない。通常nativeの比較結果と既存TMの書式を変えない。

既存比較器を単に拒否解除するだけでは受け入れない。初回反例、同一/異種対称、改変と比較中変更、CLI/Study/GUI保存、通常TE/TM回帰を確認してから限定受入とする。新規外部資料・依存・legacy参照なし。

## 元半領域方式の候補検証

`out/te-reflected-convergence-source-candidate-20260909/report.json` はPASS。製品コード外の検証器で、円筒P2/曲面P2×磁気/電気対称×2水準の8実FEMを解いた。版4をread_te_runで全再検証し、保存された元半領域Case/mesh/係数から半領域を再構成して既存比較器へ渡した。元の半領域FEMから直接保存して比較した結果と、全電場/磁場/RF/ゲート/数値状態を含む文書が完全一致した。粗い条件の数値状態は円筒2条件と球形磁気がFAIL、球形電気がUNVERIFIEDで、PASSへ書き換えていない。異種対称と通常/鏡映の混在も拒否した。

候補は一時nativeを作って既存比較へ渡す検証用アダプターで、製品には未接続。実装時には再構成したTESolutionを共有の比較関数へ渡し、元native全ファイルの前後snapshotを維持することを検討する。主ツリー464対象は不変。CLI/Study/GUI、改変中比較、標準回帰は次工程の未受入事項である。

一時パッケージ `/tmp/superfish-te-reflected-convergence-candidate-20260909` の比較器へ元半領域再構成分岐を試作した。`out/te-reflected-convergence-adapter-candidate-20260909` の4比較は元半領域方式の文書と完全一致（終了0、追加FEM 0）。candidate.patchを保持し、主ツリー464対象不変を確認。通常/鏡映混在と元物理/対称条件一致を検査し、全元nativeの前後snapshotを維持する構造だが、改変中比較・Study/CLI/GUIと標準の候補検証は未実施。主ツリーへの適用は次工程。

## 主ツリーへ接続中（基準7fcf4a7）

te_convergence.pyで版4の全native再検証後、元Case/対称条件の一致を要求し、元係数からTESolutionを再構成して既存比較へ渡す。通常/鏡映混在、左右/対称条件/規格化の変更を拒否する。返却文書にreflection_comparison（元半領域、部分スペクトルの番号、両元reflection情報）を追加し、元native全ファイルの前後snapshotを維持する。RF相対変化も元半領域で計算し、全領域への2倍則と独立に照合する。通常TE/TM文書は変えない。

GUI Studyへ元半領域比較の説明と部分スペクトル内番号の列を追加。鏡映Sweepも全順位と誤読しない説明を表示する。鏡映結果の追跡は引き続き拒否する。

追加5unit43266は終了0（30.798秒）。直線P2/曲面P2×左右×両対称の元比較全文書一致、混在/別対称/規格化拒否、source_fieldsの比較中変更拒否、反射Studyの保存と再比較を確認。out/te-reflected-convergence-development-20260909/unit.log。TE全体46952は実行中。

4種Study18357は完了出力済み（正式終了は確認待ち）。mesh PASS、固定曲面UNVERIFIED、幾何近似FAIL、固定直線UNVERIFIEDを保持し、保存再比較が一致。out/te-reflected-convergence-study-kinds-20260909。初回driverは誤った短いパラメータ名によりFEM前にstrict入力拒否。初回driver/logを保持し、正式JSONパスとadditional_uniform_refinementsへ修正した。

独立30766をscripts/validate_te_reflected_convergence.pyで実行中、out/te-reflected-convergence-independent-20260909。Chromeはout/browser-te-reflected-convergence-20260909、ログ/tmp/browser-te-reflected-convergence-20260909.log。GUI83516はlocalhost45943、workspace out/te-reflected-convergence-gui-workspace-20260909。標準は未開始。

## 統合検証の進捗

新5unitに加えTE全体46952は52件52.752秒で終了0。4種Study18357も終了0。独立30766は12実FEMで全比較文書が元半領域の比較と一致した。その後GUI列名の修正があったため、最終sourceで独立65357をout/te-reflected-convergence-final-independent-20260909へ再実行して終了0。P1両対称はUNVERIFIED、P2両対称はPASS、球形磁気FAIL/電気UNVERIFIEDを維持する。これは比較同値の合格であり、FAIL/UNVERIFIEDの物理受入ではない。

Chrome初回98052はStudy列名が部分スペクトルへ変わっていないことを検出して終了1。同名の別表を置換していたため、その変更を戻してopenStudy内へ限定した。初回report/logをout/browser-te-reflected-convergence-20260909へ保持。修正後21909はout/browser-te-reflected-convergence-fixed-20260909の7操作で終了0。3Study/6FEMの三判定、元半領域の説明、部分番号列、N/A、元nativeの場取込を確認。外部HTTP要求0、配信実装hash不変。fixed-curved.pngを目視。検証GUI83516/PID1110446はSIGINT終了0。

CLI95718はout/te-reflected-convergence-cli-20260909で固定曲面2FEMを実行して終了0。GUI独立67000はout/te-reflected-convergence-gui-independent-20260909で5ジョブの再起動、各Study点の完全native再検証、元比較文書一致、CLIのparsed Case/全係数/元case hash/数値文書一致が終了0。worker84994は中止・別の2点Study完了・再起動・元半領域比較を確認し終了0（out/te-reflected-convergence-worker-20260909）。

標準47383はout/validation-te-reflected-convergence-20260909、/tmp/validation-te-reflected-convergence-20260909.logで実行中。旧TM/通常TEの保存Study6件とTM追跡再生を追加照合中。新規外部資料・依存・legacy参照なし。標準と最終f/RF/source照合の完了までは最終受入を宣言しない。

旧Study43080は終了0。従来TM3件と通常TE3件の全6保存Studyの比較文書、既存TM Study追跡再生が完全一致（out/te-reflected-convergence-development-20260909/old_studies.json）。標準固定時のsourceは467対象。
