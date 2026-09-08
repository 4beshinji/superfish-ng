# D01/N04 曲線の親子空間における質量内積追跡

2026-09-08、直前基準8ae8037。
[曲線局所履歴](CURVED_REFINEMENT_HISTORY.md)で得たnative場を、P2係数の移送と
`∫ r³ u v dr dz` の質量内積で比較する。点サンプリングによる対応とは別の方式。
[曲線残差指標](CURVED_RESIDUAL_INDICATOR.md)による細分後に、順位と永続IDを区別するための経路である。

## 親子関係と移送

mappingをnested_curvedと明示する。同じ元弦メッシュ・同じCaseを要求し、変更できるのは
curved_refinement_levels/curved_refinement_stepsのみ。名前・モード数・規格化等の変更もこの方式では拒否する。
各側でnative履歴を再構築して幾何配列・軸/本質拘束を照合する。後の履歴は前の履歴を真に延長し、
局所markedと全域uniformの追加操作を順に合成する。複数段階の追加を許す。
旧levelsはuniform列として比較し、新履歴へ移る場合も実際の操作順序を維持する。
再メッシュ・境界再投影・履歴の途中変更・同じ水準の比較は受け付けない。
各追加操作にCaseの要素数予算と履歴で指定した品質条件を適用する。

前の係数をPで後の空間へ移送し、`X = [P u_previous, u_current]` の各列の振幅を尺度化する。
後の曲線空間で質量行列Mを再構築し、薄いQRと小さな正定値行列のCholesky分解から
`F.T F = X.T M X / scale` を満たす座標を作る。既存の直線親子追跡と同じ数式を共有した。
列Gramを直接Cholesky分解せず、一次従属したモード列の情報をRに保持する。
内積の再現差が1e-10を超えた場合は拒否する。

二次写像ではr³の次数6、P2場の積の次数4、det Jの次数2で、質量被積分関数は参照座標で最大次数12。
Duffy変換の重み込みでも8点積Gaussで多項式積分できる。ここでの「多項式積分」は丸め誤差を除く意味であり、
剛性/RFの有理被積分関数まで厳密積分できるという主張ではない。
係数特徴数 `fine_dofs × (previous_modes + current_modes)` は8388608を上限とする。

既存の重なり・割当余裕・周波数クラスタ・特異値による判定を使用する。
完全な個別対応だけにIDを与える。縮退群の基底回転は部分空間の対応に留め、
ランク低下・曖昧な割当はUNVERIFIEDとして保持する。数値丸めに応じた割当余裕の下限も適用する。
これで連続したパラメータ枝や物理誤差を保証するものではない。

## 対称条件と鏡映

直接計算したPEC/axis空間だけでなく、明示した平坦z端の電気/磁気対称条件を扱う。
両入力が鏡映済みの場合は、それぞれのreflection.source_caseで半領域の履歴を照合する。
全領域から保存規約で先頭に保持された元の半領域係数を取り出し、半領域で移送してから再鏡映する。
半領域の本質拘束と全係数の宣言された偶奇を検査する。

この写像は宣言された偶奇の部分空間に対するもの。任意の全領域P2係数への移送ではない。
鏡映した固有値の順位を、全領域の全モード順位として扱わない。
直接計算と鏡映済み計算を混ぜた比較は明示拒否する。

## 保存・CLI

既存の保存追跡要求でcontrolsを次のように指定する。

```json
{
  "mapping": "nested_curved",
  "minimum_overlap": 0.99,
  "minimum_assignment_margin": 0.05,
  "relative_cluster_gap": 0.000001,
  "minimum_relative_singular_value": 0.00000001
}
```

sample_orderは使わず、marked_cellsもここには指定しない。操作は検証済みCase履歴から得る。
これらの余計なキーは拒否する。既存要求版1のprevious_idsと版2のprevious_groupsの形式を維持する。
Pythonの直接APIはtrack_nested_curved_modes(previous, current, previous_ids, **controls)。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng track-modes request.json --out tracking.json
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng replay-mode-tracking tracking.json
```

native場の再検証・元ファイルhash照合と全追跡再計算を行う。固有値を解き直さない。
出力のphysical_mappingには追加履歴、直接/鏡映の区別、質量積分次数・内積再現差・特徴数を記録する。
既存の直線親子追跡の演算と出力は維持する。

## 検証と範囲

追加検査は、複数段階移送の手動合成一致、`P.T M_fine P = M_coarse`、
別次数の独立積分による全特徴Gram、符号/順位交換、縮退回転とランク低下、
両対称/鏡映の重なり、磁気対称鏡映保存再読込、旧levels互換、不正入力・予算・履歴改変拒否を含む。
人工的な係数交換・縮退周波数は判定ロジックの検証用であり、新しいFEM固有対とは呼ばない。

独立検証は既存の残差駆動系列を先に作り、次のように実行する。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_nested_curved_tracking.py \
  --source-root out/curved-indicator-selection-set-20260908 --out out/new-nested-curved
```

元系列の作成はscripts/validate_curved_residual_indicator.pyを参照。
合成円筒・楕円・双曲線×尺度1/2×3水準の18 native場を再検証し、12組を追跡する。
最初の組ではCLIの作成・再検証も実行する。独立質量Galerkin、先頭2モードのID/重なり、
円筒五量・RF差・Maxwell相似則を照合し、元nativeファイルを変更しない。
この検証は保存場を使う追跡であり、新規固有値計算を行ったとは扱わない。

曲線の追跡付き適応停止/保存再開/GUI、一般形状の精度/効率・幾何近似誤差・物理誤差上界は残る。

## 実行証拠

着手前637件中635合格・2 skip（395.581秒）。追加5検査は初回PASS（14.391秒）。
独立検証out/nested-curved-initial-20260908は初回PASS。18 native場を再検証した12組で先頭2個別IDを保持。
最小主重なり0.9999995273989757、質量Galerkin差最大1.288e-15、特徴内積再現差最大1.057e-15。
尺度間の主重なり差ゼロ、五量相似則差最大1.033e-13。円筒解析五量の既存許容値を維持した。
元nativeファイルと検証中ソースは変更なし、記録hashは最終ソースに一致。新規固有値計算を行ったとは扱わない。

最終標準検証 out/validation-nested-curved-20260908 は642件中640合格・2 skip（409.930秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致し、検証中のソース変更なし。

