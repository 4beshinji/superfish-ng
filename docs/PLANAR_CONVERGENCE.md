# 同形状の平面RF細分診断

平面RFの同形状細分診断を限定受入。元領域の四分割・係数移送、f/E/H/RF別判定、縮退/不足帯域UNVERIFIED、全水準保存再生・worker・CLI・GUIを接続した。標準879件（877合格、2skip、unittest1304.306秒）、追加14検査、独立16条件48FEM・特殊形状16条件48FEM、永続16worker、Chrome42操作、保存18診断54水準と取込2件を確認。旧平面32件/TE10件、TM seed9モード19量と513sourceも一致した。真の誤差上界・表面ピーク精度は保証しない。モード追跡、親P02と全計画は未完。

`PlanarConvergence` は独立パラメータ掃引とは別の要求で、真空・単一PEC境界の
矩形または明示単純多角形、P1/P2、TE/TM遮断断面を扱う。
`superfish_ng_planar_convergence` の `convergence_version: 1` は元Project、
元を含む `levels >= 3`、1始まりの `mode_ranks`、`max_triangles`、全閾値を保存する。
未知キー・boolによる整数代用・不足水準・重複順位・予算超過を拒否する。
全水準のメッシュを検証してからジョブを作成し、実FEMを順に解く。
上限まで勝手に水準を省略して成功とすることはない。

## 細分と係数移送

各元三角形の頂点をv0/v1/v2、共有辺中点をm01/m12/m20とする。
子三角形は `(v0,m01,m20)`、`(m01,v1,m12)`、`(m20,m12,v2)`、
`(m01,m12,m20)` の順。元要素順の4子を連続保存し、元点番号を保持した後に
辞書順の共有辺中点を追加する。この規則と全水準の明示nativeメッシュから
元要素番号 `child_index // 4` と重心座標写像を再構成し、完全一致を検証する。
同じ面積だけ、同じ接続だけ、または別順序の等価メッシュで代用できない。
初段の矩形Caseは版1を保持し、以降は同じ境界を持つ多角形Case版2で保存する。
物理・次数・要求モード数・U′・導電率・表示単位を保持する。

`refine_planar_mesh`、`planar_refinement_relation`、`planar_prolongation` が
幾何と移送のAPI。定数・一次・P2二次多項式、PEC拘束と
`Pᵀ M_f P = M_c`、`Pᵀ K_f P = K_c` を検査する。
これらは同じ離散スカラー場の移送であり、新しい固有モードの計算ではない。
元の領域を2倍にした候補への移送は質量恒等式の相対差約3で失敗した。
その先行反例を `out/planar-convergence-development-20260910/preflight.log` に保持する。

## 比較と判定

`compare_planar_convergence(request, solutions)` は全Case・空間・保存係数の
PEC、正スペクトル、規格化、残差を再検証する。元/子のスカラー場の面積内積を
質量行列と移送から評価し、同順位の内積が行・列双方で一意に優勢か確認する。
近接固有値、上側隣接モードの不足、対応の曖昧さは `UNVERIFIED`。
この版は縮退部分空間や一般的な順位変更を追跡しない。

スカラー内積から得た一つの符号を電場・磁場の双方に適用する。
子三角形の積分点を元要素の重心座標へ写像し、元のP1/P2係数と各解の
実固有周波数から全real/quadrature E/H成分を評価する。
表示用の補間・平坦色は使用しない。面積Gauss積分で
`||phase F_coarse - F_fine|| / ||F_fine||` をE/H別に計算する。

既定の相対差閾値はf=1e-4、E/H各0.01、RF=0.005。
対応条件は相対固有周波数間隔0.001、正規化内積0.9、競合との差0.1。
隣接間隔はさらに、対象と隣接順位の細分周波数変化の最大値の2倍を超えることを要求する。
P1の正方形TM12/TM21は解析的に縮退するが、離散分裂が固定間隔閾値を超える
先行反例があったため、この保守的な条件を追加した。これは誤差上界の推定ではない。
必要間隔と観測した細分変化も保存する。反例は
`out/planar-convergence-gap-preflight-20260910` に保持する。
RFにはU′、電気/磁気エネルギー、P′、Rs、Q0、Gの相対差を全て記録する。
両R/QはN/Aを保持する。最後の三水準の二比較が対応条件を満たし、
最後のf/E/H/RF最大差が各閾値内かつ前回以下なら各量をPASSとする。
丸め誤差の判定幅は `max(1e-12, previous_difference * 1e-8)`。
適合細分における周波数増加が相対1e-10を超える場合も未確認とする。
閾値・前回差・今回差・単調性・対応できない理由を結果に保存する。

これは最後の三水準の細分差診断で、真の離散化誤差の上界ではない。
代数残差とは別の指標であり、G/Qや体積場の安定から角の連続表面ピークの
精度を保証しない。表面ピーク精度は `not_checked`。

## 実行・保存・GUI

Python APIは `planar_convergence_jobs.execute_planar_convergence`、
`read_planar_convergence`、`JobManager.start_planar_convergence`。
CLIは `execute-planar-convergence REQUEST --out FRESH_DIRECTORY` と
`replay-planar-convergence DIRECTORY`。

親は `convergence.json`、`convergence-results.json`、状態、manifestを保存する。
`point-0000`以降に全水準のProject・状態・manifest・5つのnativeファイルを保持する。
再生は全必要ファイルのhash、子Projectと要求細分、実装由来、保存場を検証し、
診断文書全体を再計算して照合する。hashを更新しただけの判定改変も拒否する。
要求/ソースの途中変更、完了ジョブの再実行、リンク、欠落・余分な水準を拒否する。
ジョブの `complete` と数値診断の `PASS/UNVERIFIED` は別の状態。

`/planar.html` の「同じ断面の細分診断」で要求の編集・保存・読込・実行・中止、
結果の保存と履歴復元、水準のnative取込・場表示を行う。
軸対称追跡の候補には混入させない。

## 検証記録

追加unitは幾何4、比較4、保存ジョブ5、GUI1。
矩形・三角形・凹領域、回転・二尺度の幾何/行列不変量と、
P1/P2・TE/TMのE/H差を独立のM/K二次形式と照合した。
保存判定・位相・閾値・bool順位の再hash改変、kindの変更、
投入後と完了時の要求変更、実workerの中止・再起動と水準取込、CLI往復を検査した。
修正後のChromeは新7・旧Study8・旧平面13・旧軸対称10・再起動4の計42項目が合格し、外部HTTP要求なし・実行中source変更なしを記録した。
証拠は `out/browser-planar-convergence-final-20260910` と
`out/browser-{study,planar,axis}-regression-convergence-final-20260910`、
`out/browser-planar-convergence-restarted-20260910`。
GUIの全6水準を独立6FEMと照合し、元native/取込バイトと診断downloadも一致した。
`out/planar-convergence-gui-independent-final-20260910` に14.516秒の記録を保持する。

矩形・三角形の二尺度×P1/P2×TE/TM、16条件48FEMの独立解析比較は241.133秒で合格。
粗いP1（8→16→32）の8条件は解析f/場の精度不足を確認し、診断もUNVERIFIED。
細かいP2（16→32→64）の8条件は解析誤差と診断の双方がPASS。
f、全場、独立80点境界積分のG/Q、体積エネルギーを別に照合し、P2の最大相対誤差は
f=1.055e-7、縦場=7.111e-6、横場=4.594e-4、G=0.001245、Q=0.001246、U′=5.813e-13。
既定のf=1e-4・場=0.01・G/Q=0.005の解析検査閾値は変更しなかった。
記録は `out/planar-convergence-independent-refined-20260910`。
正方形/凹領域の二尺度×P1/P2×TE/TMの16条件48FEMでも、縮退未確認、
エネルギー、尺度則を33.467秒で確認した。
`out/planar-convergence-special-cases-fixed-20260910` に保持する。

矩形P2の8→16→32では、fと場が安定してもRF差0.007085が閾値を超え、
UNVERIFIEDだった。16→32→64へ細分し、閾値を緩めず再検査した。
最初の大規模P1解析試行は反例修正のため中止したもので、完了証拠には含めない。
初期標準実行は編集との重複によるsource変更検出1件で失敗し、修正前の標準実行も中止した。
検証スクリプトのNumPy bool JSON変換とGUIワークスペースの余分なjobsパスを修正した再実行を、
製品の数値修正とは区別する。修正前モジュールを保持するGUIは停止・再起動して検査をやり直した。
各失敗・中止logは元のoutディレクトリに保持する。
標準 `out/validation-planar-convergence-fixed-final-20260910` は879件中877合格・2skip（unittest1304.306秒）で終了0。
既存TM seed9モード19量はf差0・RF最大8.882e-16。旧平面32件/TE10件も再生PASS。
`out/planar-convergence-workflow-20260910` の16実worker・48水準と、実行中の中止・管理器再起動がPASS。
GUI2診断と合わせた18診断54水準・取込2件を、GUI終了後に別の管理器で再検証した。
`out/planar-convergence-persistence-20260910` と最終 `seed_regression.json` に保存hashと513sourceの一致を保持。
最終の独立検証・標準・全ブラウザーのsourceが一致し、全GUIサーバーは終了した。
既存の.manager.lock ResourceWarningは原因未解決のまま記録し、抑制していない。
次は[平面モード追跡](PLANAR_TRACKING_PLAN.md)。親集計8受入/10調査実装中/14他/1候補=33を維持する。
