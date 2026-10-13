# 元P2制限による境界再メッシュ生成API

現行追補：[04完全保存再生/CLI](CURVED_BOUNDARY_REMESH_SAVED.md)をDONE。
以下の保存未実装記述は03受入時点の履歴。次は05のStudy/GUI。

2026-10-13 JST、ADD-N04-boundary-remesh-03 **DONE**。
先行入力commit `7470986`、[固定仕様](CURVED_BOUNDARY_REMESH_SPEC.md)に従う版2生成を接続した。
全136カードは85 DONE/2 IN_PROGRESS/49 PLANNED、原123は76/2/45。
次は04の生成条件を含む完全保存再生/CLI。親N04と全goalは継続する。

## 実装と維持する意味

`curved_remesh_generation.generate_curved_remesh_plan`はstrict版2だけを新専用helperへ渡す。
元の版1body、P2制限、要素行列、FEM求解、RF/追跡/Case/Projectの核は変更していない。
版2の元境界は初期P2区間から作る。正準境界多角形だけから内部seedを作り、
要求された新履歴の後ろにサイズ超過要素のmarked制限を追加する。
全markedの分割辺/遷移対角線を固定し、既存版1置換計画として返す。

元Caseの全辺・境界・角近傍のサイズを最終native端点弦で検査する。
角近傍の基準は元境界多角形の角で固定し、追加子頂点を角として扱わない。
P2接線角はseedと全prefix、弦角は最終メッシュに原下限を適用する。
全区間P2一致、正Jacobian、辺/領域の適合、軸・タグ・TE反射は既存nativeと置換APIで確認する。
最後に固定履歴を再生し、全幾何配列の完全一致とサイズ条件を照合する。
元Caseは履歴以外を保持する。新分割を解析曲線へ再投影しない。

`_restriction_counts`は子の物理座標を作る前に既存最長辺閉包の辺集合から
`子要素数 = 親要素数 + 各親の分割辺数の総和`、
`子境界辺数 = 親境界辺数 + 分割する境界辺数`を求める。
uniformはそれぞれ4倍/2倍。既存核を変更せず、この予測値と実生成後の個数を照合する。
旧最終メッシュが新予算より大きい粗化も許すが、新seed/全新prefixの予算超過は拒否する。
元区間の併合、限界未達の部分計画、品質閾値の緩和は行わない。

## 先行失敗と修正

版2未接続の元sourceで、矩形/非アフィンの領域保存testがunknown-key ERRORになることを
先に再現し、`red.log`を保全した。仕様工程の版1サイズ競合反例も保持する。

初回の選択41件は40 PASS/1 ERROR。メッシュを省略したProjectで、元Caseによる初期meshを
一度確定した後も、seed用の緩い作業Caseで初期meshを再生成していた。
そのため元境界区間数を変え、最終弦角4.13604689度が元5度下限を満たさず正しく拒否された。
元下限を変更せず、元Caseで確定したmeshをseed Projectへ明示した。
明示meshを既に持つ場合は従来と同じ元meshを渡す。
この変更だけをASTで照合し、失敗した自動生成/独立番号の一件を再検査した。
新sourceは、同じ元meshを明示した場合と生成計画が完全一致する。

## 受入証拠と範囲

| 検査 | 実結果 |
|---|---|
| 新生成10件 | 矩形/非アフィン、全区間係数、別P2基底8×8 Duffy三積分/Green面積・体積、Hφ=r質量、Case全サイズ、親子K/M、尺度、独立内部/番号/自動source、粗化、順序付き固定履歴、予算/品質/反復、TE両端二タグ×反射有無を確認 |
| 独立数値ゲート | 面積・体積・`∫r³drdz`相対3e-12、組立Mのu=1質量も3e-12、親子K/M相対norm1e-10以内。尺度2の座標/接続/pattern一致と4/8/32則。全区間係数は元512epsゲート以内 |
| 実サイズ例 | 矩形128要素/32境界辺、非アフィン84/28。最大辺/弦面積が原上限×(1+1e-12)以下。Caseの全辺.06、非axis境界.04、元角近傍.025 mを別測定で確認 |
| 粗化と予算 | 旧矩形512要素/64境界辺を、新上限128/32で128/32へ置換。上限4境界辺のmarked/uniformは子生成器を呼ぶ前に拒否。元区間数未満/サイズ競合/旧pattern/要素/Case/反復/角度も拒否 |
| 入力9件 | 版2strict検査・未知/重複/不正型・固定履歴の独立コピー・旧版互換。未接続拒否testをstrict検査後の専用dispatch確認へ更新 |
| 直接消費22件 | 旧生成9、Project置換8、marked制限5。元CLI排他/重複、再投影拒否、全幾何/質量、非アフィン変形、親子場/勾配/行列、旧予算を確認 |
| 実行 | 初回41件71.505秒、handle9897終了1、40 PASS/1 ERROR。修正一件3.705秒、handle10018終了0/OK。計41個別PASSを分割受入し、成功40件は再実行しない |
| 源 | 元1452対象からgeneration module・入力test・例READMEを変更、新生成testを追加して1453対象。他1449源byte一致。旧生成moduleは版2分岐/説明と新helper以外の全AST一致 |

上記は生成/幾何/行列の受入で、固有値・実E/H・RFの連続物理精度の受入ではない。
新FEM/seed/full/GUI/legacy0。新例のtestはsolver.solve禁止で実行し、他の選択unitも固有値を解かない。
既存seedのFEM/RF核と版1処理を変更していないため、元seed f/RF/fullを重複実行しない。
06では仕様の専用6実FEMと保存元場を別ゲートで確認する。04〜06未完了のまま親を閉じない。

既存CLIの裸plan経路は同APIを呼ぶため版2設定を受け取れるが、生成条件を含む七項目文書、
その完全再生CLI、GUI/Study workerの新操作受入はまだない。既存GUIへJSONを渡せるだけで05完了としない。
公開APIは正常二例に対応したため、仕様例READMEの時点表示も更新した。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync python -m unittest -v test_curved_boundary_remesh test_curved_boundary_remesh_input test_curved_remesh_generation test_curved_project_remesh test_curved_marked_refinement
```

rawは`out/n04-boundary-remesh-core-20261013/`。
開始snapshot、元module/input test、red/selected/implicit-source-fix log、初回実装/新test、
受入後全source snapshotと`acceptance.json`を保持する。全実行handleは終端。
既存P2制限と公開数学的保存則を再利用し、新外部資料・依存・legacyコード/バイナリを導入していない。
